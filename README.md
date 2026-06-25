# Operator Precedence Parser

A simple compiler-construction project that implements an operator precedence parser with a Tkinter-based graphical user interface.

## Features
- Parses a context-free grammar from the GUI
- Builds an operator precedence table
- Parses input strings using operator precedence rules
- Displays parsing steps, grammar information, and the parse tree
- Supports loading grammar and input from a text file

## Project Files
- `operator_precedence_parser.py` — main application
- `test_operator_precedence_parser.py` — unit tests for file-based grammar extraction

## How to Run
Run the application with:

```bash
py operator_precedence_parser.py
```

## Loading Grammar from a Text File
You can load grammar and input from a `.txt` file by clicking the `Load .txt` button in the GUI.

The file can contain either:
- grammar and input separated by a blank line, or
- labeled sections such as:

```text
GRAMMAR:
E -> E + E | E * E | id

INPUT:
id + id * id
```

## Testing
Run the tests with:

```bash
py -m unittest -q test_operator_precedence_parser.py
```

## Example Grammar
```text
E -> E + E | E * E | ( E ) | id
```

## License
This project is for educational purposes.
