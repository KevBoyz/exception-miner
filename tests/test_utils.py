import os
import tempfile
import unittest

from utils import read_projects, to_utf8


class TestReadProjects(unittest.TestCase):
    def _write_csv(self, content):
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        self.addCleanup(os.remove, path)
        return path

    def test_csv_with_header(self):
        path = self._write_csv(
            ",name,repo,source\n"
            "kivy,kivy,https://github.com/kivy/kivy,github\n")

        projects = read_projects(path)

        self.assertEqual(list(projects['name']), ['kivy'])
        self.assertEqual(list(projects['repo']), ['https://github.com/kivy/kivy'])

    def test_csv_without_header_keeps_first_row(self):
        path = self._write_csv(
            "bup,bup,https://github.com/bup/bup,github\n"
            "wummel,linkchecker,https://github.com/wummel/linkchecker,github")

        projects = read_projects(path)

        self.assertEqual(list(projects['name']), ['bup', 'linkchecker'])
        self.assertEqual(list(projects['repo']), [
            'https://github.com/bup/bup',
            'https://github.com/wummel/linkchecker'])


class TestToUtf8(unittest.TestCase):
    def test_utf8_content_is_unchanged(self):
        content = "def f():\n    return 'ação'\n".encode('utf-8')

        self.assertEqual(to_utf8(content), content)

    def test_uses_pep263_coding_declaration(self):
        source = "# -*- coding: iso-8859-1 -*-\ndef f():\n    return 'Straße'\n"

        actual = to_utf8(source.encode('iso-8859-1'))

        self.assertEqual(actual.decode('utf-8'), source)

    def test_invalid_bytes_without_declaration_are_replaced(self):
        content = b"def f():\n    return '\xdf'\n"

        actual = to_utf8(content)

        self.assertEqual(actual.decode('utf-8'), "def f():\n    return '�'\n")


if __name__ == '__main__':
    unittest.main()
