# Operator Precedence Parser — Code Documentation

## 1. Overview
This project implements an Operator Precedence Parser with a graphical user interface (GUI) built using Tkinter. The program accepts a context-free grammar, builds an operator precedence table, parses an input string, and displays the parsing steps, grammar summary, and parse tree.

The file containing the implementation is:
- operator_precedence_parser.py

## 2. What the Program Does
The application performs the following tasks:
1. Reads a grammar written in CFG form.
2. Extracts non-terminals and operators.
3. Computes LEADING and TRAILING sets.
4. Builds a precedence relation table.
5. Parses an input string using the operator precedence algorithm.
6. Displays the parsing process and parse tree in a GUI.

---

## 3. Main Code Segments and Their Purpose

### 3.1 Module 1 — CFG Parser / Reader
This section is responsible for reading and organizing the grammar.

#### Functions

##### parse_cfg(cfg_text)
- Takes the grammar entered by the user as text.
- Splits the grammar into separate lines.
- Checks whether each rule contains the arrow symbol `->`.
- Converts each production into a list of grammar symbols.
- Returns:
  - a dictionary of productions, or
  - a list of errors if the grammar is invalid.

Example:
```text
E -> E + E | E * E | id
```
This is converted into a structure such as:
```python
{'E': [['E', '+', 'E'], ['E', '*', 'E'], ['id']]} 
```

##### tokenize_rhs(rhs)
- Breaks a right-hand side of a grammar rule into individual tokens.
- Recognizes identifiers such as `E`, `id`, `plus`, or `expr`.
- Also treats punctuation such as `+`, `*`, `(`, `)` as separate symbols.

##### get_non_terminals(productions)
- Returns all non-terminal symbols from the grammar.
- In this project, the left-hand side of each production is treated as a non-terminal.

##### extract_operators(productions)
- Finds all terminal symbols that appear in the productions.
- Adds `$` as the end-of-input marker.
- These terminals are later used to build the precedence table.

---

### 3.2 Module 2 — Precedence Table Builder
This module builds the operator precedence table based on the grammar.

#### Functions

##### compute_leading(productions)
- Computes the LEADING set for each non-terminal.
- The LEADING set contains terminals that can appear first in strings derived from that non-terminal.
- This is used to decide shift relations in the parsing table.

##### compute_trailing(productions)
- Computes the TRAILING set for each non-terminal.
- The TRAILING set contains terminals that can appear last in strings derived from that non-terminal.
- This is used to decide reduce relations.

##### build_precedence_table(productions)
- Builds the precedence relations between operators.
- It creates relations of the following forms:
  - `<·` : yields relation (shift)
  - `·>` : takes relation (reduce)
  - `=·` : equal relation

The table is built using standard operator-precedence rules:
- If two terminals appear adjacent in a production, they get an equal relation.
- If a terminal is followed by a non-terminal, the relation is used to determine shift behavior.
- If a non-terminal is followed by a terminal, reduce relations are created using its trailing symbols.

It also adds boundary rules for `$`:
- `$ <· t` for each terminal `t`
- `t ·> $` for end-of-input handling
- `$ =· $` for acceptance

---

### 3.3 Module 3 — Parsing Engine
This module actually parses the input string.

#### Functions

##### tokenize_input(input_str, operators, non_terminals)
- Splits the user-entered input into tokens.
- Validates each token against the grammar terminals.
- Returns either:
  - a list of tokens, or
  - an error list if invalid tokens are found.

##### parse_with_operator_precedence(input_tokens, prec_table, productions)
This is the core parser.

It uses a stack-based approach similar to classic operator precedence parsing.

#### How the parser works
1. Initialize an empty parse stack with `$`.
2. Add the input tokens followed by `$`.
3. Compare the top terminal on the stack with the current input token.
4. Decide whether to:
   - shift the current token onto the stack, or
   - reduce a handle on the stack.
5. When the stack reaches the accepting state, parsing is successful.

#### Important internal helpers

##### make_node(label, children=None)
- Creates a dictionary representation of a parse tree node.
- Each node has:
  - a label
  - a list of children

##### top_terminal(stk)
- Looks at the stack and returns the highest terminal symbol visible near the top.
- This is used to compare precedence relations.

##### find_production(handle)
- Tries to match a handle (the portion of the stack that forms a production) to a grammar rule.
- If a match is found, it returns the left-hand side non-terminal.

#### Parsing logic
- If the precedence relation is `<·` or `=·`, the parser shifts the current token.
- If the relation is `·>`, the parser reduces using the handle found on the stack.
- A reduction replaces the handle with the corresponding non-terminal and builds a parse tree node.
- The parse continues until either the input is accepted or an error occurs.

#### Output of the parser
The function returns:
- a list of parse steps,
- a result string such as `Accepted` or `Rejected`,
- the root node of the parse tree (if parsing succeeded).

---

### 3.4 Module 4 — GUI Layer
This section creates the visual interface of the application.

#### The App class
The entire interface is built inside the `App` class.

#### UI layout
The GUI is divided into:
- a left panel for grammar input and input string
- a right panel with multiple tabs:
  - Parsing Steps
  - Precedence Table
  - Grammar Info
  - Parse Tree

#### Main UI components

##### _build_ui()
- Creates the overall structure of the window.
- Adds the header, body, left panel, and right panel.

##### _build_left()
- Creates the input area for the grammar.
- Creates the input string field.
- Adds the Parse and Clear buttons.
- Displays the parse result.
- Shows developer information.

##### _build_right()
- Creates notebook tabs for showing different results.

##### _build_steps_tab()
- Displays a table of parsing steps.
- Each row shows:
  - step number
  - current stack
  - remaining input
  - action taken

##### _build_prec_tab()
- Displays the precedence table in a scrollable canvas.
- Each cell shows the relation between two symbols.

##### _build_grammar_tab()
- Shows the grammar summary, productions, LEADING sets, and TRAILING sets.

##### _build_tree_tab()
- Creates a drawing area where the parse tree will be shown after a successful parse.

---

## 4. UI Functionality and Event Logic

### 4.1 Parse Button
When the user clicks the Parse button:
1. The current grammar is read from the text box.
2. The grammar is validated.
3. The precedence table is built.
4. The input string is tokenized.
5. The parser runs.
6. The results are displayed in the tabs.

This is handled by the `_run()` method.

### 4.2 Clear Button
The Clear button resets all UI outputs and clears the result display.
This is handled by `_clear()`.

### 4.3 Result Display
After parsing:
- If the parse succeeds, the result label becomes green and shows `ACCEPTED`.
- If parsing fails, the label becomes red and shows `REJECTED`.

### 4.4 Logging
The program uses a small log area to show messages such as:
- grammar accepted
- tokens accepted
- parsing steps
- errors

---

## 5. Parse Tree Logic
The parse tree is not stored as a traditional tree structure from the start. Instead, it is built incrementally during parsing.

### How it works
- Every time a token is shifted, a leaf node is created.
- Every time a reduction happens, a new internal node is created.
- The node’s children are the nodes that represent the symbols in the reduced handle.

### Example
If the grammar reduces the handle:
```text
id + id
```
into the non-terminal `E`, the parser creates an `E` node whose children are the corresponding nodes of the symbols in the handle.

### Drawing the parse tree
The `_show_parse_tree()` method:
1. Computes the number of leaves.
2. Computes the maximum depth of the tree.
3. Assigns positions to each node.
4. Draws rectangles for nodes and lines for parent-child connections.

This gives a visual tree representation in the GUI.

---

## 6. Step-by-Step Parsing Flow
The parser follows this pattern:
1. Read the grammar.
2. Build precedence relations.
3. Tokenize the input.
4. Start with stack containing `$`.
5. Compare the current input symbol and the stack top.
6. Shift or reduce accordingly.
7. Continue until the input is fully consumed.
8. Accept or reject depending on the final state.

---

## 7. Example of a Typical Run
If the user enters the grammar:
```text
E -> E + E | E * E | ( E ) | id
```
And enters the input:
```text
id + id * id
```
The program will:
- build the precedence table,
- show the shift/reduce steps,
- produce a successful parse tree if the grammar and input are valid.

---

## 8. Important Notes
- The parser is designed for operator precedence parsing, not full predictive parsing.
- It is suitable for a simple grammar where operator precedence relations can be derived.
- The GUI is built with Tkinter and is easy to run on a local machine with Python installed.

---

## 9. How to Run the Application
Run the file using Python:
```bash
python operator_precedence_parser.py
```

---

## 10. Summary
This project demonstrates the complete workflow of an operator precedence parser:
- grammar reading,
- precedence construction,
- parsing,
- parse tree creation,
- and visualization through a Tkinter GUI.

It is a strong example of how compiler construction concepts can be implemented in a practical, interactive application.
