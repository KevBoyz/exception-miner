import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

from cli import cmdline_args
from utils import clear_directory, clear_projects


def _can_symlink():
    tmp = tempfile.mkdtemp()
    try:
        os.symlink('.', os.path.join(tmp, 'loop'), target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _write(path, content=''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


class TestClearDirectory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_removes_contents_and_keeps_directory(self):
        output = os.path.join(self.tmp, 'output')
        _write(os.path.join(output, 'parser', 'py', 'bup_stats.csv'))
        _write(os.path.join(output, 'call_graph', 'bup', 'call_graph.json'))
        _write(os.path.join(output, 'loose.txt'))

        clear_directory(output)

        self.assertTrue(os.path.isdir(output))
        self.assertEqual(os.listdir(output), [])

    def test_removes_read_only_files(self):
        # git clones keep .git/objects read-only, which Windows refuses to delete
        output = os.path.join(self.tmp, 'output')
        obj = os.path.join(output, 'repo', '.git', 'objects', 'ab', 'cdef')
        top = os.path.join(output, 'read_only.txt')
        for path in [obj, top]:
            _write(path)
            os.chmod(path, stat.S_IREAD)

        clear_directory(output)

        self.assertEqual(os.listdir(output), [])

    def test_missing_directory_is_noop(self):
        self.assertEqual(clear_directory(os.path.join(self.tmp, 'missing')), [])

    @unittest.skipUnless(_can_symlink(), 'symlinks not supported')
    def test_does_not_follow_symlinks(self):
        outside = os.path.join(self.tmp, 'outside')
        _write(os.path.join(outside, 'keep.txt'))
        output = os.path.join(self.tmp, 'output')
        os.makedirs(output)
        os.symlink(outside, os.path.join(output, 'link'), target_is_directory=True)

        clear_directory(output)

        self.assertEqual(os.listdir(output), [])
        self.assertTrue(os.path.isfile(os.path.join(outside, 'keep.txt')))


class TestClearProjects(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_removes_projects_and_keeps_language_folders(self):
        projects = os.path.join(self.tmp, 'projects')
        _write(os.path.join(projects, 'py', 'bup', 'setup.py'))
        _write(os.path.join(projects, 'py', 'Sick-Beard', 'SickBeard.py'))
        _write(os.path.join(projects, 'ts', 'app', 'index.ts'))

        removed = clear_projects(projects)

        self.assertEqual(sorted(os.listdir(projects)), ['py', 'ts'])
        self.assertEqual(os.listdir(os.path.join(projects, 'py')), [])
        self.assertEqual(os.listdir(os.path.join(projects, 'ts')), [])
        self.assertEqual(len(removed), 3)

    def test_missing_projects_directory_is_noop(self):
        self.assertEqual(clear_projects(os.path.join(self.tmp, 'missing')), [])


class TestClearArgs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_clear_with_output_and_projects(self):
        output = os.path.join(self.tmp, 'out')

        args = cmdline_args(['clear', '-o', output, '-p'])

        self.assertEqual(args.command, 'clear')
        self.assertEqual(args.output_dir, output)
        self.assertTrue(args.projects)

    def test_clear_defaults(self):
        args = cmdline_args(['clear'])

        self.assertEqual(args.command, 'clear')
        self.assertEqual(args.output_dir, 'output')
        self.assertFalse(args.projects)

    def test_clear_refuses_directory_containing_cwd(self):
        # "-o ." would wipe the repository itself
        for output in ['.', os.path.dirname(os.getcwd())]:
            with self.subTest(output=output):
                with self.assertRaises(SystemExit):
                    cmdline_args(['clear', '-o', output])

    def test_clear_command_does_not_load_parsers(self):
        # tree-sitter parsers are imported for mining only; loading them prints a FutureWarning
        miner = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'miner.py')
        _write(os.path.join(self.tmp, 'out', 'old.csv'))

        result = subprocess.run([sys.executable, miner, 'clear', '-o', 'out'],
                                cwd=self.tmp, capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('FutureWarning', result.stderr)
        self.assertIn('Clear finished: 1 item(s) removed', result.stdout)

    def test_mining_args_still_work(self):
        csv_path = os.path.join(self.tmp, 'input.csv')
        _write(csv_path, ',name,repo,source\n')
        output = os.path.join(self.tmp, 'out')

        args = cmdline_args(['-in', csv_path, '-o', output, '-lang', 'python'])

        self.assertEqual(args.command, 'mine')
        self.assertEqual(args.input_path, csv_path)
        self.assertEqual(args.language, ['python'])
