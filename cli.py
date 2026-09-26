import os
import sys
import argparse
from utils import dictionary


def _contains(parent, child):
    parent = os.path.normcase(os.path.realpath(parent))
    child = os.path.normcase(os.path.realpath(child))
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:  # different drives on Windows
        return False


def clear_args(argv):
    args = argparse.ArgumentParser(prog='miner.py clear', description='Remove the results of previous runs')

    args.add_argument('-o', '--output_dir', default='output', metavar='', help='Path to the output directory to clear (its contents are removed)')
    args.add_argument('-p', '--projects', action='store_true', help='Also remove the cloned projects (projects/<lang>/<project>), keeping the projects/<lang> folders')
    parsed_args = args.parse_args(argv)
    parsed_args.command = 'clear'

    # Refuse to clear a directory that holds the repository or the working directory (e.g. "-o .")
    source_dir = os.path.dirname(os.path.abspath(__file__))
    if _contains(parsed_args.output_dir, os.getcwd()) or _contains(parsed_args.output_dir, source_dir):
        sys.stderr.write(f"Refusing to clear {parsed_args.output_dir}: it contains the working directory or the miner source\n")
        sys.exit(1)

    return parsed_args


def cmdline_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == 'clear':
        return clear_args(argv[1:])

    args = argparse.ArgumentParser(description='', epilog="Run 'miner.py clear -h' to remove the results of previous runs", formatter_class=argparse.RawDescriptionHelpFormatter)

    args.add_argument('-o', '--output_dir', default='output', metavar='', help='Path to the output directory')
    args.add_argument('-in', '--input_path', required=True, metavar='', help='Path to the file csv that contains the name, repo and source')
    # Create a string with all available languages
    available_languages = ', '.join(dictionary.keys())
    language_help = f'Programming language of the input file(s). Available options: {available_languages}'
    args.add_argument('-lang', '--language', nargs='+', default=['python'], metavar='', help=language_help)
    parsed_args = args.parse_args(argv)
    parsed_args.command = 'mine'

    # Check if the input file exists
    if not os.path.isfile(parsed_args.input_path):
        sys.stderr.write(f"The input file does not exist: {parsed_args.input_path}\n")
        sys.exit(1)

    _, file_extension = os.path.splitext(parsed_args.input_path)
    file_extension = file_extension[1:]  # remove the leading dot

    # Check if the file extension is CSV
    if file_extension.lower() != 'csv':
        sys.stderr.write(f"The input file must be a CSV file, but got a .{file_extension} file\n")
        sys.exit(1)

    # Check if the output directory exists, if not create it
    if not os.path.isdir(parsed_args.output_dir):
        os.makedirs(parsed_args.output_dir)

    # Check if the provided language is supported
    for language in parsed_args.language:
        if language not in dictionary.keys():
            sys.stderr.write(f"The provided language is not supported: {language}\n")
            sys.stderr.write("Supported languages are: " + ", ".join(dictionary.keys()) + "\n")
            sys.exit(1)

    return parsed_args

if sys.version_info < (3, 10):
    sys.stderr.write("You need Python 3.10 or later to run this script\n")
    sys.exit(1)
