from tree_sitter._binding import Query

from tree_sitter_languages import get_language, get_parser


TS_LANGUAGE = get_language('typescript')

parser = get_parser('typescript')
parser.set_language(TS_LANGUAGE)

QUERY_FUNCTION_DEF: Query = TS_LANGUAGE.query(
    "(function_declaration) @function.def")

QUERY_ARROW_FUNCTION_DEF: Query = TS_LANGUAGE.query(
    """(variable_declarator 
            (identifier)?
            (arrow_function
                body: (statement_block)
            )
        ) @function.def
    """
)

QUERY_FUNCTION_IDENTIFIER: Query = TS_LANGUAGE.query(
    """(function_declaration (identifier) @function.def)""")

QUERY_FUNCTION_BODY: Query = TS_LANGUAGE.query(
    """(function_declaration body: (statement_block) @body)""")

QUERY_EXPRESSION_STATEMENT: Query = TS_LANGUAGE.query(
    """(expression_statement) @expression.stmt""")

QUERY_TRY_STMT: Query = TS_LANGUAGE.query(
    """(try_statement) @try.statement""")

QUERY_TRY_CATCH: Query = TS_LANGUAGE.query(
    """(try_statement
        (catch_clause)* @catch.clause) @try.stmt""")

QUERY_CATCH_CLAUSE: Query = TS_LANGUAGE.query(
    """(catch_clause) @catch.clause""")

QUERY_CATCH_IDENTIFIER_BODY: Query = TS_LANGUAGE.query(
    """(catch_clause 
        (identifier)? @catch.identifier 
        (statement_block) @catch.body
    )""")

QUERY_CATCH_BLOCK: Query = TS_LANGUAGE.query(
    """(catch_clause (statement_block) @body)""")

QUERY_CATCH_STATEMENTS: Query = TS_LANGUAGE.query(
    """(catch_clause (statement_block [(_) @catch.expression]*))""")
#Não entendi
QUERY_CATCH_EXPRESSION: Query = TS_LANGUAGE.query(
    """(catch_clause (_) @catch.expression)""")

QUERY_FIND_IDENTIFIERS: Query = TS_LANGUAGE.query(
    """(identifier) @identifier""")

QUERY_THROW_STATEMENT: Query = TS_LANGUAGE.query(
    """(throw_statement) @throw.stmt""")

QUERY_THROW_STATEMENT_IDENTIFIER: Query = TS_LANGUAGE.query(
    """(throw_statement [
                (identifier) @throw.identifier
                (new_expression constructor: (identifier) @throw.identifier)
                (call_expression function: (identifier) @throw.identifier)
            ]*)""")

QUERY_THROW_STATEMENT_CHILDREN: Query = TS_LANGUAGE.query(
    """(throw_statement (_) @throw.identifier)""")

QUERY_RETURN: Query = TS_LANGUAGE.query(
    """(return_statement) @return.stmt""")

QUERY_FINALLY_BLOCK: Query = TS_LANGUAGE.query(
    """(finally_clause) @finally.stmt""")

QUERY_CATCH_ASSIGNMENT_EXPRESSION_LEFT: Query = TS_LANGUAGE.query(
    """(catch_clause 
        (identifier)? @catch.identifier 
        (statement_block
        	(expression_statement
            	(assignment_expression left: (identifier) @left.assignment.identifier)
            )
        )
    )""")

# every exception metric is computed from one of these nodes: a function without them
# has all metrics zeroed (see FileStats.get_metrics)
QUERY_EXCEPTION_NODES: Query = TS_LANGUAGE.query(
    """[(try_statement) (catch_clause) (finally_clause) (throw_statement)] @exception.node""")
