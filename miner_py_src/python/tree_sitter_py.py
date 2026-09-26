from tree_sitter._binding import Query
from tree_sitter_languages import get_language, get_parser

PY_LANGUAGE = get_language('python')

parser = get_parser('python')
parser.set_language(PY_LANGUAGE)

QUERY_FUNCTION_DEF: Query = PY_LANGUAGE.query(
    "(function_definition) @function.def")

QUERY_FUNCTION_IDENTIFIER: Query = PY_LANGUAGE.query(
    """(function_definition (identifier) @function.def)""")

QUERY_FUNCTION_BODY: Query = PY_LANGUAGE.query(
    """ (function_definition body: (block) @body)""")

QUERY_EXPRESSION_STATEMENT: Query = PY_LANGUAGE.query(
    """(expression_statement) @expression.stmt""")

QUERY_TRY_STMT: Query = PY_LANGUAGE.query(
    """(try_statement) @try.statement""")

QUERY_TRY_EXCEPT: Query = PY_LANGUAGE.query(
    """(try_statement
        (except_clause)* @except.clause) @try.stmt""")

QUERY_EXCEPT_CLAUSE: Query = PY_LANGUAGE.query(
    """(except_clause) @except.clause""")

QUERY_EXCEPT_BLOCK: Query = PY_LANGUAGE.query(
    """(except_clause (block) @body)""")

QUERY_EXCEPT_EXPRESSION: Query = PY_LANGUAGE.query(
    """(except_clause (_) @except.expression (block))""")

QUERY_PASS_BLOCK: Query = PY_LANGUAGE.query(
    """(block 
	(pass_statement) @pass.stmt )""")

QUERY_FIND_IDENTIFIERS: Query = PY_LANGUAGE.query(
    """(identifier) @identifier""")

QUERY_RAISE_STATEMENT: Query = PY_LANGUAGE.query(
    """(raise_statement) @raise.stmt""")

QUERY_RAISE_STATEMENT_IDENTIFIER: Query = PY_LANGUAGE.query(
    """(raise_statement [
                (identifier) @raise.identifier 
                (call function: (identifier) @raise.identifier)
            ]*)""")

QUERY_TRY_EXCEPT_RAISE: Query = PY_LANGUAGE.query(
    """(except_clause (block 
            (raise_statement [
                (identifier) @raise.identifier 
                (call function: (identifier) @raise.identifier)
            ]*) @raise.stmt))""")

QUERY_TRY_ELSE: Query = PY_LANGUAGE.query(
    """(try_statement (else_clause) @else.clause )""")

QUERY_TRY_RETURN: Query = PY_LANGUAGE.query(
    """(try_statement (block (return_statement)) @return.stmt )""")

QUERY_FINALLY_BLOCK: Query = PY_LANGUAGE.query(
    """(finally_clause) @finally.stmt""")

# every exception metric is computed from one of these nodes: a function without them
# has all metrics zeroed (see FileStats.get_metrics)
QUERY_EXCEPTION_NODES: Query = PY_LANGUAGE.query(
    """[(try_statement) (except_clause) (finally_clause) (raise_statement)] @exception.node""")
