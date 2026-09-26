import csv
import io
import os
import re
import shutil
import stat
import logging
import tokenize
import pandas as pd
from tqdm.auto import trange

# this is a hack to fool github servers in believing that this is not a robot
SLEEP_TIME = 60


class CSVOutput:
    def __init__(self, file_name, header):
        self.__file_name = self.__verify(file_name)
        self.__file_path = os.path.abspath(self.__file_name)
        self.__fields = header
        with open(self.__file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.__fields)
            writer.writeheader()

    def name(self):
        return self.__file_name

    def write(self, entry):
        with open(self.__file_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.__fields)
            writer.writerow(
                {k: v for k, v in entry.items() if k in self.__fields})

    def __verify(self, file_name, counter=1):
        if not os.path.exists(file_name):
            return file_name
        file_name = re.sub("(-[0-9]+)?\.", "-{}.".format(counter), file_name)
        return self.__verify(file_name, counter=counter + 1)


def create_logger(name, log_file):
    # Function setup as many loggers as you want
    formatter = logging.Formatter('[%(asctime)-15s] %(message)s')
    logger = logging.getLogger(name)

    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(formatter)

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(streamHandler)

    return logger


def batch(iterable, n=1):
    l = len(iterable)
    pbar = trange(0, l, n)
    for ndx in pbar:
        pbar.set_description(f"Global ... ")
        yield iterable[ndx:min(ndx + n, l)]


PROJECTS_COLUMNS = ["owner", "name", "repo", "source"]


def read_projects(input_path):
    projects = pd.read_csv(input_path, sep=",")
    if not {"name", "repo"}.issubset(projects.columns):
        # CSV without header: first row is data, not column names
        projects = pd.read_csv(input_path, sep=",", header=None, names=PROJECTS_COLUMNS)
    return projects


def to_utf8(content):
    # Parsed node text is decoded as utf-8 downstream, so normalize the source bytes
    # first, honoring a PEP 263 coding declaration (e.g. Python 2 latin-1 files)
    try:
        content.decode("utf-8")
        return content
    except UnicodeDecodeError:
        pass
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(content).readline)
        return content.decode(encoding).encode("utf-8")
    except (SyntaxError, UnicodeDecodeError):
        return content.decode("utf-8", errors="replace").encode("utf-8")


def _remove_read_only(func, path, _):
    # git keeps .git/objects read-only, which Windows refuses to delete
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clear_directory(path):
    # Remove everything inside path, keeping path itself; symlinks are removed, never followed
    if not os.path.isdir(path):
        return []
    removed = []
    for entry in sorted(os.listdir(path)):
        entry_path = os.path.join(path, entry)
        if os.path.islink(entry_path) or not os.path.isdir(entry_path):
            try:
                os.remove(entry_path)
            except PermissionError:
                _remove_read_only(os.remove, entry_path, None)
        else:
            shutil.rmtree(entry_path, onerror=_remove_read_only)
        removed.append(entry_path)
    return removed


def clear_projects(projects_dir="projects"):
    # Cloned repositories live in projects/<lang>/<project>: remove them, keep projects/<lang>
    if not os.path.isdir(projects_dir):
        return []
    removed = []
    for language_dir in sorted(os.listdir(projects_dir)):
        language_path = os.path.join(projects_dir, language_dir)
        if os.path.isdir(language_path) and not os.path.islink(language_path):
            removed += clear_directory(language_path)
    return removed

dictionary = {
    "python": {
        "main": "py",
        "additional": []
    },
    "typescript": {
        "main": "ts",
        "additional": ["tsx"]
    },
    "java": {
        "main": "java",
        "additional": []
    },
}