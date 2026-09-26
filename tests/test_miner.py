import argparse
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock
from multiprocessing import Pool

import pandas as pd

import miner
from cli import cmdline_args
from utils import dictionary

TS_FILES = {
    'a.ts': "function first() { try { work(); } catch (e) { throw e; } }\n"
            "function second() { return 1; }\n",
    'b.ts': "function third() { throw new Error('x'); }\n",
}


def _write(path, content=''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class TestCollectParser(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.language = dictionary['typescript']
        miner.init_language(self.language['main'])
        self.files = []
        for name, content in TS_FILES.items():
            path = os.path.join(self.tmp, 'src', name)
            _write(path, content)
            self.files.append(path)

    def collect(self, output_dir, pool=None):
        args = argparse.Namespace(output_dir=os.path.join(self.tmp, output_dir))
        miner.collect_parser(self.files, 'proj', self.language, args, pool)
        return os.path.join(args.output_dir, 'parser', 'ts', 'proj_stats.csv')

    def test_rows_are_newest_first(self):
        df = pd.read_csv(self.collect('out'))

        self.assertEqual(list(df['function']), ['third', 'second', 'first'])
        self.assertEqual(list(df['n_try_catch_ts']), [0, 0, 1])
        self.assertEqual(list(df['n_throw_ts']), [1, 0, 1])

    def test_pool_writes_the_same_csv(self):
        sequential = self.collect('sequential')
        with Pool(2, initializer=miner.init_language, initargs=(self.language['main'],)) as pool:
            parallel = self.collect('parallel', pool)

        with open(sequential, 'rb') as a, open(parallel, 'rb') as b:
            self.assertEqual(a.read(), b.read())

    def test_parse_file_returns_plain_rows(self):
        rows = miner.parse_file(self.files[0])

        self.assertEqual([row['function'] for row in rows], ['first', 'second'])
        self.assertEqual(rows[0]['file'], self.files[0])
        self.assertEqual(rows[0]['str_uncaught_exceptions'], '')


class TestFetchRepositories(TempDirTestCase):
    def setUp(self):
        super().setUp()
        cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, cwd)
        self.language = dictionary['python']
        self.args = argparse.Namespace(output_dir='out')

    def test_skips_clone_when_repository_is_present(self):
        project = os.path.join(self.tmp, 'projects', 'py', 'proj')
        _write(os.path.join(project, 'mod.py'), 'def f():\n    pass\n')
        subprocess.run(['git', 'init', '-q', project], check=True)

        with unittest.mock.patch.object(miner, 'call') as call:
            files = miner.fetch_repositories('proj', 'https://example.com/proj', self.language, self.args)

        call.assert_not_called()
        self.assertEqual([os.path.normpath(f) for f in files], [os.path.join(project, 'mod.py')])

    def test_clones_shallow_when_repository_is_missing(self):
        with unittest.mock.patch.object(miner, 'call') as call:
            files = miner.fetch_repositories('proj', 'https://example.com/proj', self.language, self.args)

        call.assert_called_once()
        self.assertIn('git clone --depth 1 https://example.com/proj.git --recursive', call.call_args[0][0])
        self.assertEqual(files, [])  # the clone is mocked: nothing to list


class TestJobsArgument(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.input_path = os.path.join(self.tmp, 'in.csv')
        _write(self.input_path, ',name,repo,source\n')
        self.output_dir = os.path.join(self.tmp, 'out')

    def test_default_is_cpu_count(self):
        args = cmdline_args(['-in', self.input_path, '-o', self.output_dir])

        self.assertEqual(args.jobs, os.cpu_count())

    def test_jobs(self):
        args = cmdline_args(['-in', self.input_path, '-o', self.output_dir, '-j', '3'])

        self.assertEqual(args.jobs, 3)

    def test_rejects_less_than_one(self):
        with unittest.mock.patch('sys.stderr'), self.assertRaises(SystemExit):
            cmdline_args(['-in', self.input_path, '-o', self.output_dir, '-j', '0'])


if __name__ == '__main__':
    unittest.main()
