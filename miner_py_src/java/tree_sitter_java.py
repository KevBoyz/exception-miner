from tree_sitter._binding import Query

from tree_sitter_languages import get_language, get_parser

JAVA_LANGUAGE = get_language('java')

parser = get_parser('java')
parser.set_language(JAVA_LANGUAGE)

QUERY_METHOD_DEF: Query = JAVA_LANGUAGE.query(
    "(method_declaration) @function.def")

QUERY_METHOD_IDENTIFIER: Query = JAVA_LANGUAGE.query(
    """(method_declaration (identifier) @function.def)""")

QUERY_METHOD_BODY: Query = JAVA_LANGUAGE.query(
    """(method_declaration body: (block) @body)""")

QUERY_METHOD_INVOCATION: Query = JAVA_LANGUAGE.query(
    """(method_invocation (identifier) @method.invocation)""")

QUERY_EXPRESSION_STATEMENT: Query = JAVA_LANGUAGE.query(
    """(expression_statement) @expression.stmt""")

QUERY_TRY_STMT: Query = JAVA_LANGUAGE.query(
    """(try_statement) @try.statement""")


QUERY_TRY_CATCH: Query = JAVA_LANGUAGE.query(
    """(try_statement
        (catch_clause)* @catch.clause) @try.stmt""")


QUERY_CATCH_CLAUSE: Query = JAVA_LANGUAGE.query(
    """(catch_clause) @catch.clause""")

QUERY_CATCH_IDENTIFIER_BODY: Query = JAVA_LANGUAGE.query(
    """
     (catch_clause 
        (catch_formal_parameter 
            (catch_type (type_identifier)? @catch.type)
            (identifier)? @catch.identifier)
        (block) @catch.body
    )
    """
)

QUERY_METHOD_INVOCATION: Query = JAVA_LANGUAGE.query(
    """(method_invocation (identifier) @method.invocation)""")


QUERY_RETURN: Query = JAVA_LANGUAGE.query(
    """(return_statement) @return.stmt""")

QUERY_CATCH_BLOCK = JAVA_LANGUAGE.query("""
    (catch_clause (catch_formal_parameter) @parameter (block) @body)
""")

QUERY_FIND_IDENTIFIERS = JAVA_LANGUAGE.query("""
    (catch_type (type_identifier) @identifier)
""")

QUERY_CATCH_STATEMENTS: Query = JAVA_LANGUAGE.query(
    """(catch_clause (block [(_) @catch.expression]*))""")

QUERY_INSTANCEOF_EXPRESSION: Query = JAVA_LANGUAGE.query(
    """(instanceof_expression) @instanceof.expr""")

QUERY_CATCH_EXPRESSION: Query = JAVA_LANGUAGE.query(
    """(catch_clause (_) @catch.expression)""")

QUERY_FIND_IDENTIFIERS_THROW: Query = JAVA_LANGUAGE.query(
   """(type_identifier) @throw.identifier """)

QUERY_THROW_STATEMENT: Query = JAVA_LANGUAGE.query(
    """(throw_statement) @throw.stmt""")

# QUERY_THROW_STATEMENT_IDENTIFIER: Query = JAVA_LANGUAGE.query(
#     """(throw_statement 
# 	(object_creation_expression
#                 (type_identifier) @throw.identifier
#             ) @throw.identifier)""")

QUERY_THROW_STATEMENT_IDENTIFIER: Query = JAVA_LANGUAGE.query(
    """(throw_statement 
    (object_creation_expression
                (type_identifier) @throw.new.identifier
            ) @throw.new.identifier)
       (throw_statement 
        (identifier) @throw.existing.identifier)""")

QUERY_FINALLY_BLOCK: Query = JAVA_LANGUAGE.query(
    """ (finally_clause) @finally.clause""")

QUERY_CATCH_ASSIGNMENT_EXPRESSION_LEFT: Query = JAVA_LANGUAGE.query(
    """(catch_clause 
        (catch_formal_parameter 
            (identifier) @catch.identifier)
        (block
            (expression_statement
                (assignment_expression 
                    left: (identifier) @left.assignment.identifier
                )
            )
        ) @catch.body
    )""")

# every exception metric is computed from one of these nodes: a function without them
# has all metrics zeroed (see FileStats.get_metrics)
QUERY_EXCEPTION_NODES: Query = JAVA_LANGUAGE.query(
    """[(try_statement) (catch_clause) (finally_clause) (throw_statement)] @exception.node""")
