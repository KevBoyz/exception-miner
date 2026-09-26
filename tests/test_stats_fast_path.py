import unittest

from miner_py_src.java import miner_java_utils, tree_sitter_java
from miner_py_src.java import stats as java_stats
from miner_py_src.python import miner_py_utils, tree_sitter_py
from miner_py_src.python import stats as python_stats
from miner_py_src.typescript import miner_ts_utils, tree_sitter_ts
from miner_py_src.typescript import stats as ts_stats

PYTHON_SOURCE = b"""
def plain(a):
    return a + 1

def with_try():
    try:
        work()
    except ValueError as e:
        pass
    finally:
        done()

def with_raise(x):
    if x:
        raise Exception('x')

def outer():
    def inner():
        try:
            work()
        except:
            raise
    return inner
"""

TS_SOURCE = b"""
function plain(a: number) { return a + 1; }

function withTry() {
    try { work(); } catch (e) { throw new Error(e); } finally { done(); }
}

function withThrow(x) { if (x) { throw 'x'; } }

const arrow = () => { return 1; };
"""

JAVA_SOURCE = b"""
class A {
    int plain(int a) { return a + 1; }

    void withTry() {
        try { work(); } catch (Exception e) { throw new RuntimeException(e); } finally { done(); }
    }

    void withThrow(boolean x) { if (x) { throw new NullPointerException(); } }
}
"""


class TestNoExceptionFastPath(unittest.TestCase):
    """get_metrics skips the queries for functions without exception nodes: the result
    must be exactly what the full computation returns, for every function"""

    def assert_same_metrics(self, tree_sitter, utils, stats, source, expected_functions):
        functions = utils.get_function_defs(tree_sitter.parser.parse(source))
        self.assertEqual(len(functions), expected_functions)
        for function in functions:
            fast = stats.FileStats().get_metrics(function)
            full = stats.FileStats()._compute_metrics(function)
            self.assertEqual(fast, full, function.text)
            self.assertEqual(list(fast), list(full))  # same column order
            self.assertEqual([type(v) for v in fast.values()], [type(v) for v in full.values()])

    def test_python(self):
        self.assert_same_metrics(tree_sitter_py, miner_py_utils, python_stats, PYTHON_SOURCE, 5)

    def test_typescript(self):
        self.assert_same_metrics(tree_sitter_ts, miner_ts_utils, ts_stats, TS_SOURCE, 4)

    def test_java(self):
        self.assert_same_metrics(tree_sitter_java, miner_java_utils, java_stats, JAVA_SOURCE, 3)

    def test_cached_result_is_not_shared(self):
        function = miner_py_utils.get_function_defs(tree_sitter_py.parser.parse(PYTHON_SOURCE))[0]
        first = python_stats.FileStats().get_metrics(function)
        first['n_raise'] = 99

        self.assertEqual(python_stats.FileStats().get_metrics(function)['n_raise'], 0)


if __name__ == '__main__':
    unittest.main()
