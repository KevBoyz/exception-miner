SBES Track Tool - Exception Miner
---
This repository includes the source code and data for our paper "Exception Miner: Multi-language Static Analysis Tool to Identify Exception Handling Anti-Patterns".

## Requirements

- Python 3.10+

## Virtualenv (Windows)
1. Run `py -3.10 -m venv {virtualenv name}`
2. Go to Scripts repository in `{virtualenv name}/Scripts`
3. Run `activate`

## Build
To reproduce the results, follow the instructions below.

1. Back to root directory
2. Run `pip install -r requirements.txt` 

## Usage

1. Run the script with the command `python miner.py -in <input_path> -o <output_dir> -lang <language>`

### Parameters

- `<input_path>`: Path to the CSV file that contains the name, repo, and source. This is a required parameter.
- `<output_dir>`: Path to the output directory. If not provided, the default is `output`.
- `<language>`: Programming language of the input file(s). Available options are python, typescript. If not provided, the default is `python`.

### Example

To run the script on a CSV file named `input.csv`, output the results to a directory named `results`, and specify the language as `python`, you would use the following command:

```bash
python miner.py -in input.csv -o results -lang python
```

### Cleaning previous runs

To start a new run from scratch, remove the results of previous runs with the `clear` command:

```bash
python miner.py clear -o <output_dir> -p
```

- `-o <output_dir>`: Output directory whose contents are removed (the directory itself is kept). If not provided, the default is `output`.
- `-p`: Also remove the cloned projects in `projects/<language>/<project>`, keeping the `projects/<language>` folders. Without it, `projects` is left untouched.

For example, `python miner.py clear -o results -p` empties `results` and removes every cloned project. The command refuses an output directory that contains the working directory or the miner source (e.g. `-o .`).

## Unit tests
To run the unit tests, follow the instructions below.

1. Run `python3 -m unittest`

## Coverage report  
To generate the coverage report, follow the instructions below.

1. Run `coverage run -m unittest`
2. Run `coverage report --omit *test_*,*__init__*`

## Results
The CSV containing the complete results from all exception handling anti-patterns in Python, Java, and Typescript is available in the `results` folder.

## Recording link containing the tool demonstration
https://drive.google.com/file/d/1q3VAcssSlwitu9ZKBP7dRwK-n0vvf0fh/view