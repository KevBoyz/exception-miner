from collections import Counter
from .miner_ts_utils import (
    count_catch,
    is_generic_catch,
    count_useless_catch,
    count_empty_catch,
    count_catch_reassigning_identifier,
    count_throw,
    count_untyped_throw,
    count_non_generic_throw,
    count_not_recommended_throw,
    count_try_catch_throw,
    count_try_return,
    count_finally,
    count_nested_try,
    statement_couter,
    get_catch_identifiers,
    get_throw_identifiers,
    get_catch_clause,
    get_catch_block,
    n_wrapped_catch
)
from tqdm import tqdm
from tree_sitter._binding import Node
from .miner_ts_utils import QUERY_TRY_STMT, QUERY_CATCH_CLAUSE
from .tree_sitter_ts import QUERY_EXCEPTION_NODES


class FileStats:
    _no_exception_metrics = None
    num_files = 0
    num_functions = 0
    files_try_catch = set()
    files_try_pass = set()
    files_generic_catch = set()
    func_try_catch = set()
    func_try_pass = set()
    func_generic_catch = set()
    func_has_except_handler = set()
    func_has_nested_try = set()

    def metrics(self, func_def: Node, file_path: str):
        if len(QUERY_TRY_STMT.captures(func_def)) != 0:
            self.files_try_catch.add(file_path)

        captures_catch = QUERY_CATCH_CLAUSE.captures(func_def)

        for catch_clause, _ in captures_catch:
            self.func_try_catch.add(f"{file_path}:{func_def.id}")
            if is_generic_catch(catch_clause):
                tqdm.write(f"{file_path}:{func_def.id}")
                self.files_generic_catch.add(file_path)
                self.func_generic_catch.add(f"{file_path}:{func_def.id}")

    def __str__(self) -> str:
        return (
            f"\n---------------- try-except STATS -----------------\n"
            f"# try-catch found:                   {len(self.func_try_catch)}\n"
            f"% try-catch per file:                {(len(self.files_try_catch) / self.num_files) * 100:.2f}%\n"
            f"% try-catch per function definition: {(len(self.func_try_catch) / max(self.num_functions, 1)) * 100:.2f}%\n"
            f"\n--------------- bad practice STATS ----------------\n"
            f"# generic catch handling:         {len(self.func_generic_catch)}\n"
            f"# generic catch per file:         {(len(self.files_generic_catch) / self.num_files) * 100:.2f}%\n"
            f"# generic catch per function definition: {(len(self.func_generic_catch) / max(self.num_functions, 1)) * 100:.2f}%\n"
        )

    def get_metrics(self, func_def: Node):
        # every metric comes from a try/catch/finally/throw node, so all functions without
        # them get the same result: compute it once instead of running every query
        if len(QUERY_EXCEPTION_NODES.captures(func_def)) == 0:
            if FileStats._no_exception_metrics is None:
                FileStats._no_exception_metrics = self._compute_metrics(func_def)
            return dict(FileStats._no_exception_metrics)
        return self._compute_metrics(func_def)

    def _compute_metrics(self, func_def: Node):
        n_try_catch, n_generic_catch, = 0, 0

        captures_catch = get_catch_clause(func_def)

        n_captures_try_catch_throw = count_try_catch_throw(func_def)

        n_useless_catch = count_useless_catch(func_def)

        n_count_empty_catch = count_empty_catch(func_def)

        n_count_catch_reassigning_identifier = count_catch_reassigning_identifier(func_def)

        n_throw = count_throw(func_def)

        n_generic_throw = count_untyped_throw(func_def)

        n_non_generic_throw = count_non_generic_throw(func_def)

        n_not_recommended_throw = count_not_recommended_throw(func_def)

        n_try_return = count_try_return(func_def)

        n_nested_try = count_nested_try(func_def)

        n_finally = count_finally(func_def)

        n_wrapped_catch_ = n_wrapped_catch(func_def)
    
        captures_catch_ids = get_catch_identifiers(func_def)

        captures_throw_ident = get_throw_identifiers(func_def)

        captures_catch_block = list(map(lambda x: x[0].text.decode('utf-8'), get_catch_block(func_def)))
        
        for catch_clause, _ in captures_catch:
            n_try_catch += 1
            if is_generic_catch(catch_clause):
                n_generic_catch += 1

        str_catch_identifiers = " ".join(captures_catch_ids)
        str_throw_identifiers = " ".join(captures_throw_ident)
        str_catch_block = " ".join(captures_catch_block)

        return {
            "n_try_catch_ts": n_try_catch,
            "n_finally_ts": n_finally,
            "str_catch_identifiers_ts": str_catch_identifiers,
            "str_catch_block_ts": str_catch_block,
            "n_generic_catch_ts": n_generic_catch,
            "n_useless_catch_ts": n_useless_catch,
            "n_wrapped_catch_ts": n_wrapped_catch_,
            "n_count_empty_catch_ts": n_count_empty_catch,
            "n_count_catch_reassigning_identifier_ts": n_count_catch_reassigning_identifier,
            "str_throw_identifiers_ts": str_throw_identifiers,
            "n_throw_ts": n_throw,
            "n_generic_throw_ts": n_generic_throw,
            "n_non_generic_throw_ts": n_non_generic_throw,
            "n_not_recommended_throw_ts": n_not_recommended_throw,
            "n_captures_try_catch_throw_ts": n_captures_try_catch_throw,
            "n_try_return_ts": n_try_return,
            "n_nested_try_ts": n_nested_try, 
        }

class TBLDStats:
    functions_count = 0
    try_num_eq_1 = 0
    try_num_lt_eq_2 = 0
    tokens_count = 0
    num_max_tokens = 0
    statements_count = 0
    num_max_statement = 0
    unique_tokens = Counter()
    function_tokens_acc = 0

    def increment_try_stats(self, try_count):
        if try_count == 1:
            self.try_num_eq_1 += 1
        elif try_count >= 2:
            self.try_num_lt_eq_2 += 1

    def __str__(self) -> str:
        stats_str = (
            "-------- TBLD STATS --------\n"
            f"#Python methods   {self.functions_count}\n"
            f"#TryNum=1         {self.try_num_eq_1}\n"
            f"#TryNum≥2         {self.try_num_lt_eq_2}\n"
            f"#MaxTokens        {self.num_max_tokens}\n"
            f"#AverageTokens    {self.tokens_count / self.functions_count if self.functions_count != 0 else 0:.2f}\n"
            f"#MaxStatements    {self.num_max_statement}\n"
            f"#AverageStatement {(self.statements_count / self.functions_count) if self.functions_count != 0 else 0:.2f}\n"
            f"#UniqueTokens     {len(self.unique_tokens)}\n"
            "-------- Top 10 Unique Tokens Ranking --------\n"
        )

        unique_ranking_str = "".join(
            [
                f"{key} - {value}" + "\n"
                for key, value in self.unique_tokens.most_common()[:10]
            ]
        )
        return stats_str + unique_ranking_str


class CBGDStats:
    functions_count = 0
    catch_num_eq_1 = 0
    catch_num_lt_eq_2 = 0
    tokens_count_source = 0
    tokens_count_target = 0
    num_max_tokens_source = 0
    num_max_tokens_target = 0
    statements_count = 0
    num_max_statement = 0
    unique_tokens = Counter()
    function_tokens_source_acc = 0
    function_tokens_target_acc = 0

    current_num_tokens = 0

    def reset(self):
        self.num_max_tokens_source = max(
            self.num_max_tokens_source, self.function_tokens_source_acc
        )
        self.tokens_count_source += self.function_tokens_source_acc
        self.function_tokens_source_acc = 0

        self.num_max_tokens_target = max(
            self.num_max_tokens_target, self.function_tokens_target_acc
        )
        self.tokens_count_target += self.function_tokens_target_acc
        self.function_tokens_target_acc = 0

    def increment_catch_stats(self, function_def: Node):
        except_count = count_catch(function_def)
        if except_count == 1:
            self.catch_num_eq_1 += 1
        elif except_count >= 2:
            self.catch_num_lt_eq_2 += 1

    def increment_function_counter(self):
        self.functions_count += 1

    def increment_statements_counter(self, function_def: Node):
        num_statements = statement_couter(function_def)
        self.statements_count += num_statements
        self.num_max_statement = max(self.num_max_statement, num_statements)

    def increment_current_num_tokens(self, num_tokens):
        self.current_num_tokens = num_tokens

    def move_current_num_tokens_source(self):
        self.function_tokens_source_acc += self.current_num_tokens
        self.current_num_tokens = 0

    def move_current_num_tokens_target(self):
        self.function_tokens_target_acc += self.current_num_tokens
        self.current_num_tokens = 0

    def __str__(self) -> str:
        stats_str = (
            "-------- CBGD STATS --------\n"
            f"#Try-catch pairs         {self.functions_count}\n"
            f"#CatchNum=1             {self.catch_num_eq_1}\n"
            f"#CatchNum≥2             {self.catch_num_lt_eq_2}\n"
            f"#MaxTokens of Source     {self.num_max_tokens_source}\n"
            f"#AverageTokens of Source {self.tokens_count_source / self.functions_count if self.functions_count != 0 else 0:.2f}\n"
            f"#MaxTokens of Target     {self.num_max_tokens_target}\n"
            f"#AverageTokens of Target {self.tokens_count_target / self.functions_count if self.functions_count != 0 else 0:.2f}\n"
            f"#UniqueTokens            {len(self.unique_tokens)}\n"
            "-------- Top 10 Unique Tokens Ranking --------\n"
        )

        unique_ranking_str = "".join(
            [
                f"{key} - {value}" + "\n"
                for key, value in self.unique_tokens.most_common()[:10]
            ]
        )
        return stats_str + unique_ranking_str
