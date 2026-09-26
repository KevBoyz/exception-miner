import json
import os
import subprocess
import sys

from tqdm import tqdm

from miner_py_src.python.exceptions import CallGraphError

# PyCG's import hook turns every module first imported during the analysis into an
# empty stub. CPython imports unicodedata to normalize non-ASCII identifiers, so a
# stubbed one breaks ast.parse ("module 'unicodedata' has no attribute 'normalize'").
PYCG_LAUNCHER = ("import sys, unicodedata; from pycg.__main__ import main; "
                 "sys.argv[0] = 'pycg'; main()")

def list_python_files(root):
    # os.walk does not follow directory symlinks. glob's '**' does and never ends on
    # self-referencing links (e.g. bup's Documentation/man1 -> .)
    python_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # skip hidden entries, like glob does
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if (filename.endswith('.py') and not filename.startswith('.')
                    and os.path.isfile(path) and not os.path.islink(path)):
                python_files.append(os.path.abspath(path))
    return python_files

def generate_cfg(project_name, project_folder, output_dir):
    current_path = os.getcwd()
    os.makedirs(
        f'{current_path}/{output_dir}/call_graph/{project_name}', exist_ok=True)
    # no os.chdir: the cwd is shared by the whole process (the next project is cloned by
    # another thread meanwhile), so PyCG gets the project folder as its own cwd instead
    project_path = os.path.normpath(project_folder)
    tqdm.write(f"Generating call graph for {project_name}...")

    # python_src_files = [os.path.abspath(x)
    #                     for x in glob.iglob(f"./**/{project_src_base}/**/*.py", recursive=True)]
    # if len(python_src_files) == 0:
    #     raise CallGraphError(f"No python files found in {project_src_base}")

    #python_src_files = project_src_base

    python_src_files = list_python_files(project_path)

    if len(python_src_files) == 0:
        raise CallGraphError("No python files found")

    tqdm.write(f'found {len(python_src_files)} files')
    tqdm.write('Running PyCG...')

    args = [
        sys.executable, '-c', PYCG_LAUNCHER,
        *python_src_files[0:4],
        '--package', project_name,
        '--max-iter', '1',
        '--output', f'{current_path}/{output_dir}/call_graph/{project_name}/call_graph.json']

    # TODO: Paralelize? (Too Slow Here...)
    proc = subprocess.run(args, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, cwd=project_path)

    tqdm.write('PyCG finished')

    if (proc.returncode != 0):
        raise CallGraphError(proc.stderr.decode('utf-8', errors='replace'))

    try:
        open(f'{current_path}/{output_dir}/call_graph/{project_name}/stdout.txt', 'w').write(
            proc.stdout.decode('utf-8'))
    except IOError as e:
        tqdm.write('Could not write stdout.txt')
        tqdm.write(e.strerror)

    try:
        open(f'{current_path}/{output_dir}/call_graph/{project_name}/stderr.txt', 'w').write(
            proc.stderr.decode('utf-8'))
    except IOError as e:
        tqdm.write('Could not write stderr.txt')
        tqdm.write(e.strerror)

    json_obj = json.load(
        open(f'{current_path}/{output_dir}/call_graph/{project_name}/call_graph.json'))
    call_graph = {}
    for func_name, calls in json_obj.items():
        if func_name not in call_graph.keys():
            call_graph[func_name] = {
                'calls': [],
                'called_by': [],
            }

        for call in calls:
            call_graph[func_name]['calls'].append(call)

            if call not in call_graph.keys():
                call_graph[call] = {
                    'calls': [],
                    'called_by': [],
                }
            call_graph[call]['called_by'] = call_graph[call]['called_by'] or []
            call_graph[call]['called_by'].append(func_name)

    return call_graph


class CFG():
    def __init__(self, graph, catch_nodes):
        self.catch_nodes = catch_nodes
        self.graph = graph

    # def get_uncaught_exceptions(self, func_name: str, raise_types: list[str]) -> dict[str, list[str]]:
    def get_uncaught_exceptions(self, func_name: str, raise_types: list) -> dict:
        if (func_name not in self.graph.keys()):
            raise CallGraphError(f"CFG: {func_name} not found")

        # export_data: dict[str, list[str]] = {}
        export_data = {}

        if len(self.graph[func_name]['called_by']) == 0:
            return export_data  # API call ??

        for called_by in self.graph[func_name]['called_by']:
            if called_by not in self.catch_nodes.keys():
                export_data[called_by] = raise_types
                continue

            for raise_type in raise_types:
                if raise_type not in self.catch_nodes[called_by]:
                    if called_by not in export_data.keys():
                        export_data[called_by] = []

                    export_data[called_by].append(raise_type)
                    export_data[called_by] = list(set(export_data[called_by]))

        return export_data
