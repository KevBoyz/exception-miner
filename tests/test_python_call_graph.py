import os
import shutil
import tempfile
import unittest
import unittest.mock

from miner_py_src.python.call_graph import generate_cfg, list_python_files
from miner_py_src.python.exceptions import CallGraphError


def _can_symlink():
    tmp = tempfile.mkdtemp()
    try:
        os.symlink('.', os.path.join(tmp, 'loop'), target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(os.chdir, self.cwd)


class TestGenerateCFG(TempDirTestCase):
    def setUp(self):
        super().setUp()
        os.chdir(self.tmp)

    # UTF-8 mode makes PyCG read sources as utf-8 on Windows too, like on Linux
    @unittest.mock.patch.dict(os.environ, {'PYTHONUTF8': '1'})
    def test_non_ascii_identifiers(self):
        _write(os.path.join(self.tmp, 'proj', 'mod.py'),
               "def função():\n    return 1\n\n\n"
               "def caller():\n    return função()\n")

        call_graph = generate_cfg('proj', 'proj', 'out')

        # PyCG prefixes module names with a relative path ('...mod' on Linux)
        callers = [name for name in call_graph if name.endswith('mod.caller')]
        self.assertEqual(len(callers), 1, call_graph)
        self.assertTrue(
            any(c.endswith('mod.função') for c in call_graph[callers[0]]['calls']))

    def test_restores_cwd_on_error(self):
        os.makedirs(os.path.join(self.tmp, 'empty'))

        with self.assertRaises(CallGraphError):
            generate_cfg('empty', 'empty', 'out')

        self.assertEqual(os.getcwd(), self.tmp)


class TestListPythonFiles(TempDirTestCase):
    def test_lists_python_files_recursively(self):
        _write(os.path.join(self.tmp, 'a.py'), '')
        _write(os.path.join(self.tmp, 'pkg', 'b.py'), '')
        _write(os.path.join(self.tmp, 'pkg', 'notes.txt'), '')
        _write(os.path.join(self.tmp, '.hidden', 'c.py'), '')

        actual = list_python_files(self.tmp)

        self.assertCountEqual(actual, [
            os.path.join(self.tmp, 'a.py'),
            os.path.join(self.tmp, 'pkg', 'b.py')])

    @unittest.skipUnless(_can_symlink(), 'symlinks not supported')
    def test_does_not_follow_symlinks(self):
        _write(os.path.join(self.tmp, 'a.py'), '')
        _write(os.path.join(self.tmp, 'docs', 'b.py'), '')
        # self-referencing links, like bup's Documentation/man1 -> .
        for i in range(1, 10):
            os.symlink('.', os.path.join(self.tmp, 'docs', f'man{i}'),
                       target_is_directory=True)
        os.symlink('a.py', os.path.join(self.tmp, 'link.py'))

        actual = list_python_files(self.tmp)

        self.assertCountEqual(actual, [
            os.path.join(self.tmp, 'a.py'),
            os.path.join(self.tmp, 'docs', 'b.py')])


if __name__ == '__main__':
    unittest.main()
