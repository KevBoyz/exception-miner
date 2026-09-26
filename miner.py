import os
import sys
import pathlib
from subprocess import call
from typing import List
from cli import cmdline_args
from utils import clear_directory, clear_projects


def clear(args):
    removed = clear_directory(args.output_dir)
    if args.projects:
        removed += clear_projects()
    for path in removed:
        print(f"Removed {path}")
    print(f"Clear finished: {len(removed)} item(s) removed")

# clear runs before the imports below: it needs none of the parsers, and loading them
# is slow and prints a tree-sitter FutureWarning
if __name__ == "__main__":
    args = cmdline_args()
    if args.command == 'clear':
        clear(args)
        sys.exit(0)

import pandas as pd
from pydriller import Git
from tqdm import tqdm

from utils import create_logger, dictionary, read_projects, to_utf8
import json

from miner_py_src.java import tree_sitter_java, exception, miner_java_utils
from miner_py_src.java import stats as java_stats
from miner_py_src.python import tree_sitter_py, exceptions, miner_py_utils
from miner_py_src.python import stats as python_stats
from miner_py_src.python.call_graph import CFG, generate_cfg
from miner_py_src.python.exceptions import CallGraphError
from miner_py_src.typescript import tree_sitter_ts, exceptions, miner_ts_utils
from miner_py_src.typescript import stats as ts_stats
from multiprocessing import Process

logger = create_logger("exception_miner", "exception_miner.log")


MODULES = {
    "py": {
        "tree_sitter": tree_sitter_py,
        "stats": python_stats,
        "exception": exceptions,
        "utils": miner_py_utils,
    },
    "ts": {
        "tree_sitter": tree_sitter_ts,
        "stats": ts_stats,
        "exception": exceptions,
        "utils": miner_ts_utils
    },
    "java": {
        "tree_sitter": tree_sitter_java,
        "stats": java_stats,
        "exception": exception,
        "utils": miner_java_utils
    }
}

def fetch_gh(projects, dir='projects/py/'):
    for index, row in projects.iterrows():
        project = row['name']
        try:
            path = os.path.join(os.getcwd(), dir, project)
            git_cmd = "git clone {}.git --recursive {}".format(
                row['repo'], path)
            call(git_cmd, shell=True)
            logger.warning("EH MINING: cloned project")
        except Exception as e:
            logger.warning(f"EH MINING: error cloing project {project} {e}")

def file_match(suffix, language):
    extension = suffix[1:]
    return extension == language['main'] or extension in language['additional']

def fetch_repositories(project, repo, language, args)->list[str]:

    # projects = pd.read_csv("projects.csv", sep=",")
    # for index, row in projects.iterrows():
    # repo = Repository(row['repo'], clone_repo_to="projects")
    # for commit in Repository(row['repo'], clone_repo_to="projects").traverse_commits():
    # project = row["name"]

    mainExtension = language["main"]

    if not os.path.exists(f"{args.output_dir}/pytlint"):
        os.makedirs(f"{args.output_dir}/pytlint")

    if not os.path.exists(f"{args.output_dir}/pytlint/{project}"):
        os.mkdir(f"{args.output_dir}/pytlint/{project}")

    try:
        path = os.path.join(os.getcwd(), f"projects/{mainExtension}", str(project))
        git_cmd = "git clone {}.git --recursive {}".format(repo, path)
        call(git_cmd, shell=True)
        logger.warning(
            "Exception Miner: Before init git repo: {}".format(project))
        gr = Git(path)
        logger.warning(
            "Exception Miner: After init git repo: {}".format(project))

        files = [
            f
            for f in gr.files()
            if file_match(pathlib.Path(rf"{f}").suffix, language) and not os.path.islink(f)
        ]

        return files

    except Exception as ex:
        logger.warning(
            "Exception Miner: error in project: {}, error: {}".format(
                project, str(ex))
        )
        return []

def __get_method_name(node):  # -> str | None:
    for child in node.children:
        if child.type == 'identifier' or child.type == 'object_pattern':
            return child.text.decode("utf-8")

def collect_parser(files, project_name, language, args):
    columnsLanguage = {
        "py": ["file", "function", "func_body", "str_uncaught_exceptions", "n_try_except", "n_try_pass", "n_finally",
                 "n_generic_except", "n_raise", "n_captures_broad_raise", "n_captures_try_except_raise", "n_captures_misplaced_bare_raise",
                 "n_try_else", "n_try_return", "str_except_identifiers", "str_raise_identifiers", "str_except_block", "n_nested_try", 
                 "n_bare_except", "n_bare_raise_finally"], 
        "ts": ["file", "function", "func_body","n_try_catch_ts","n_finally_ts","str_catch_identifiers_ts","str_catch_block_ts","n_generic_catch_ts","n_useless_catch_ts","n_count_empty_catch_ts","n_count_catch_reassigning_identifier_ts",
                "n_wrapped_catch_ts","str_throw_identifiers_ts","n_throw_ts","n_generic_throw_ts","n_non_generic_throw_ts","n_not_recommended_throw_ts",
                "n_captures_try_catch_throw_ts","n_try_return_ts","n_nested_try_ts" ],
        "java": ["file", "function", "func_body", 'n_try_catch_java', 'n_finally_java', 'str_catch_identifiers_java', 'str_catch_block_java', 'n_generic_catch_java', 'n_useless_catch_java', 'n_wrapped_catch_java', 'n_count_empty_catch_java', 'n_count_catch_reassigning_identifier_java', 'str_throw_identifiers_java', 'n_throw_java', 'n_generic_throw_java', 'n_non_generic_throw_java', 'n_captures_try_catch_throw_java', 'n_try_return_java', 'n_nested_try_java', 'throw_within_finally_java', 'throwing_null_pointer_exception_java', 'generic_exception_handling_java', 'instanceof_in_catch_java', 'n_instanceof_in_catch_java', 'destructive_wrapping_java', 'cause_in_catch_java', 'n_cout_get_cause_in_catch_java' ]
    }

    df = pd.DataFrame(
        columns=columnsLanguage[language["main"]]
    )

    file_stats = FileStats()
    pbar = tqdm(files)
    func_defs: List[str] = []  # List[Node] = []
    for file_path in pbar:
        pbar.set_description(f"Processing {str(file_path)[-40:].ljust(40)}")

        with open(file_path, "rb") as file:
            try:
                content = file.read()
            except UnicodeDecodeError as ex:
                tqdm.write(
                    f"###### UnicodeDecodeError Error!!! file: {file_path}.\n{str(ex)}"
                )
                continue
        content = to_utf8(content)
        try:
            tree = parser.parse(content)
        except SyntaxError as ex:
            tqdm.write(
                f"###### SyntaxError Error!!! file: {file_path}.\n{str(ex)}")
        else:
            captures = get_function_defs(tree)
            for child in captures:
                function_identifier = __get_method_name(child)
                if function_identifier is None:
                    raise FunctionDefNotFoundException(
                        f'Function identifier not found:\n {child.text}')

                func_defs.append(function_identifier)
                file_stats.metrics(child, file_path)
                metrics = file_stats.get_metrics(child)
                df = pd.concat(
                    [
                        pd.DataFrame(
                            [{
                                "file": file_path,
                                "function": __get_method_name(child),
                                "func_body": child.text.decode("utf-8"),
                                'str_uncaught_exceptions': '',
                                **metrics                                
                            }],
                            columns=df.columns,
                        ),
                        df,
                    ],
                    ignore_index=True,
                )
    file_stats.num_files += len(files)
    file_stats.num_functions += len(func_defs)

    if language["main"] == 'py':
        #Call graph for python projects
        logger.warning(f"before call graph...")

        #!!!!!!!!!!!!!!!!!!
        mainExtension = language["main"]
        try:
            call_graph = generate_cfg(str(project_name), os.path.normpath(
                f"projects/{mainExtension}/{str(project_name)}"), args.output_dir)
        except CallGraphError as ex:
            logger.warning(
                f"Exception Miner: call graph failed for {project_name}, continuing without it: {ex}")
            call_graph = None

        if call_graph is None:
            call_graph = {}

        catch_nodes = {}
        raise_nodes = {}
        for func_name in call_graph.keys():
            if not func_name.startswith('...'):
                continue  # skip external libraries

            names = func_name[3:].split('.')
            if len(names) == 1:
                continue  # skip built-in functions

            module_path = '/'.join(names[0:-1])
            func_identifier = names[-1]
            print(f'func_identifier {func_identifier}')

            query = df[(df['file'].str.contains(module_path) &
                        df['function'].str.fullmatch(func_identifier))]

            if query.empty:
                continue

            if query.iloc[0]['str_raise_identifiers']:
                raise_nodes[func_name] = query.iloc[0]['str_raise_identifiers'].split(
                    ' ')
            if query.iloc[0]['str_except_identifiers']:
                catch_nodes[func_name] = query.iloc[0]['str_except_identifiers'].split(
                    ' ')
        #!!!!!!!!!!!!!!!!!!
        call_graph_cfg = CFG(call_graph, catch_nodes)
        logger.warning(f"before parse the nodes from call graph...")

        for func_name, raise_types in raise_nodes.items():
            # func_file_raise, func_identifier_raise = func_name_raise.split(':')
            cfg_uncaught_exceptions = call_graph_cfg.get_uncaught_exceptions(
                func_name, raise_types)
            if cfg_uncaught_exceptions == {}:
                continue

            for f_full_identifier, uncaught_exceptions in cfg_uncaught_exceptions.items():
                module_path, func_identifier = ('', '')
                names = f_full_identifier.split('.')
                if len(names) == 1:
                    func_identifier = names[0]
                else:
                    module_path = names[0]
                    func_identifier = names[-1]

                query = df[(df['file'].str.contains(module_path) &
                            df['function'].str.fullmatch(func_identifier))]

                if query.empty:
                    continue

                idx = int(query.iloc[0].name)  # type: ignore

                for uncaught_exception in uncaught_exceptions:
                    old_value = str(
                        df.iloc[idx, df.columns.get_loc('str_uncaught_exceptions')])

                    # append uncaught exception
                    df.iloc[idx, df.columns.get_loc(
                        'str_uncaught_exceptions')] = (old_value + f' {func_name}:{uncaught_exception}').strip()

    # func_defs_try_except = [
    #     f for f in func_defs if check_function_has_except_handler(f)
    # ]  # and not check_function_has_nested_try(f)    ]

    # func_defs_try_pass = [f for f in func_defs if is_try_except_pass(f)]
    os.makedirs(f"{args.output_dir}/parser/{language['main']}", exist_ok=True)
    logger.warning(f"Before write to csv: {df.shape}")
    df.to_csv(f"{args.output_dir}/parser/{language['main']}/{project_name}_stats.csv", index=False)

def check_language(languages):
    results=[]
    for language in languages:
        try:
            result = dictionary[language]
            results.append(result)
        except:
            raise Exception(f"This language isn't in our dataset. Please, select any of these: {', '.join(list(dictionary.keys()))}")
    return results

def process_language(language, args):
    global parser, get_function_defs, FunctionDefNotFoundException, FileStats
    module = MODULES[language['main']]

    parser = module["tree_sitter"].parser
    get_function_defs = module["utils"].get_function_defs
    FunctionDefNotFoundException = module["exception"].FunctionDefNotFoundException
    FileStats = module["stats"].FileStats

    projects = read_projects(args.input_path)
    for index, row in projects.iterrows():
        files = fetch_repositories(row['name'],row['repo'], language, args)
        if len(files) > 0:
            collect_parser(files, row['name'], language, args)

if __name__ == "__main__":
    # args were parsed at the top of the file
    languages = check_language(args.language)

    processes = []
    for language in languages:
        p = Process(target=process_language, args=(language, args))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

