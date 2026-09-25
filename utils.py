import csv
import io
import os
import re
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