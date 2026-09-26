from collections import Counter
from .miner_java_utils import (
    check_cause_in_catch,
    check_destructive_wrapping,
    check_instanceof_in_catch,
    check_throw_within_finally,
    check_throwing_null_pointer_exception,
    count_get_cause_in_catch,
    count_instanceof_in_catch,
    identify_generic_exception_handling,
    is_generic_catch,
    count_useless_catch,
    count_empty_catch,
    count_catch_reassigning_identifier,
    count_throw,
    count_untyped_throw,
    count_non_generic_throw,
    count_try_catch_throw,
    count_try_return,
    count_finally,
    count_nested_try,
    get_catch_identifiers,
    get_throw_identifiers,
    get_catch_clause,
    get_catch_block,
    n_wrapped_catch
)
from tqdm import tqdm
from tree_sitter._binding import Node
from .miner_java_utils import QUERY_TRY_STMT, QUERY_CATCH_CLAUSE
from .tree_sitter_java import QUERY_EXCEPTION_NODES

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

        n_try_return = count_try_return(func_def)

        n_nested_try = count_nested_try(func_def)

        n_finally = count_finally(func_def)

        n_wrapped_catch_ = n_wrapped_catch(func_def)

        throw_within_finally = check_throw_within_finally(func_def)  # New

        throwing_null_pointer_exception = check_throwing_null_pointer_exception(func_def)  # New

        generic_exception_handling = identify_generic_exception_handling(func_def)  # New

        instanceof_in_catch = check_instanceof_in_catch(func_def)  # New

        n_instanceof_in_catch = count_instanceof_in_catch(func_def)  # New
        
        destructive_wrapping = check_destructive_wrapping(func_def)  # New

        cause_in_catch = check_cause_in_catch(func_def)  # New

        n_cout_get_cause_in_catch = count_get_cause_in_catch(func_def)  # New    

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
            "n_try_catch_java": n_try_catch,
            "n_finally_java": n_finally,
            "str_catch_identifiers_java": str_catch_identifiers,
            "str_catch_block_java": str_catch_block,
            "n_generic_catch_java": n_generic_catch,
            "n_useless_catch_java": n_useless_catch,
            "n_wrapped_catch_java": n_wrapped_catch_,
            "n_count_empty_catch_java": n_count_empty_catch,
            "n_count_catch_reassigning_identifier_java": n_count_catch_reassigning_identifier,
            "str_throw_identifiers_java": str_throw_identifiers,
            "n_throw_java": n_throw,
            "n_generic_throw_java": n_generic_throw,
            "n_non_generic_throw_java": n_non_generic_throw,
            "n_captures_try_catch_throw_java": n_captures_try_catch_throw,
            "n_try_return_java": n_try_return,
            "n_nested_try_java": n_nested_try,
            "throw_within_finally_java": throw_within_finally,  # New
            "throwing_null_pointer_exception_java": throwing_null_pointer_exception,  # New
            "generic_exception_handling_java": generic_exception_handling,  # New
            "instanceof_in_catch_java": instanceof_in_catch,  # New
            "n_instanceof_in_catch_java": n_instanceof_in_catch,  # New
            "destructive_wrapping_java": destructive_wrapping,  # New
            "cause_in_catch_java": cause_in_catch,  # New
            "n_cout_get_cause_in_catch_java": n_cout_get_cause_in_catch,  # New 
        }