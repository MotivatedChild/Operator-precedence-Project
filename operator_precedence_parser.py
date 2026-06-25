"""
Operator Precedence Parser — GUI Application
CS3510 Compiler Construction Semester Project
=============================================
Modules:
  1. CFG Parser / Reader
  2. Precedence Table Builder
  3. Parsing Engine
  4. GUI Layer
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


def extract_cfg_and_input_from_text(content):
    """Extract grammar and input text from a user-supplied .txt file."""
    if not content:
        return "", ""

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return "", ""

    grammar_lines, input_lines = [], []
    section = "grammar"

    for line in lines:
        lowered = line.lower()
        if lowered.startswith("grammar") and ":" in line:
            section = "grammar"
            continue
        if lowered.startswith("input") and ":" in line:
            section = "input"
            continue

        if section == "input":
            input_lines.append(line)
        else:
            if "->" in line or "|" in line:
                grammar_lines.append(line)
            else:
                input_lines.append(line)

    if grammar_lines:
        grammar = "\n".join(grammar_lines).strip()
    else:
        grammar = "\n".join(lines).strip()

    input_text = " ".join(input_lines).strip()

    if not grammar_lines and "\n\n" in content:
        parts = [part.strip() for part in re.split(r"\n\s*\n", content, maxsplit=1)]
        if len(parts) == 2:
            grammar = parts[0].strip()
            input_text = parts[1].strip()

    return grammar, input_text


# ══════════════════════════════════════════════════════════════
#  MODULE 1 — CFG PARSER / READER
# ══════════════════════════════════════════════════════════════

def parse_cfg(cfg_text):
    """
    Parse CFG text into a dict of productions.
    Format:  E -> E+E | E*E | (E) | id
    Returns: {'E': [['E','+','E'], ['E','*','E'], ...]}
    """
    productions, errors = {}, []
    lines = [l.strip() for l in cfg_text.strip().splitlines() if l.strip()]
    if not lines:
        return None, ["CFG cannot be empty."]
    for line in lines:
        if '->' not in line:
            errors.append(f"Invalid rule (missing '->'): {line}"); continue
        lhs, rhs = line.split('->', 1)
        lhs = lhs.strip()
        if not lhs:
            errors.append(f"Empty LHS: {line}"); continue
        for alt in rhs.split('|'):
            toks = tokenize_rhs(alt.strip())
            if toks:
                productions.setdefault(lhs, []).append(toks)
    if errors:
        return None, errors
    if not productions:
        return None, ["No valid productions found."]
    return productions, []


def tokenize_rhs(rhs):
    """Split a RHS string into a list of grammar symbols."""
    tokens, i = [], 0
    while i < len(rhs):
        if rhs[i] == ' ':
            i += 1; continue
        m = re.match(r'[a-zA-Z_][a-zA-Z0-9_]*', rhs[i:])
        if m:
            tokens.append(m.group()); i += m.end()
        else:
            tokens.append(rhs[i]); i += 1
    return tokens


def get_non_terminals(productions):
    return set(productions.keys())


def extract_operators(productions):
    """Return sorted list of all terminals (operators) + '$'."""
    nt = get_non_terminals(productions)
    ops = {sym for prods in productions.values()
               for prod  in prods
               for sym   in prod
               if  sym not in nt}
    result = sorted(ops)
    if '$' not in result:
        result.append('$')
    return result


# ══════════════════════════════════════════════════════════════
#  MODULE 2 — PRECEDENCE TABLE BUILDER
# ══════════════════════════════════════════════════════════════

def compute_leading(productions):
    """
    LEADING(A) = set of terminals that can be the first terminal
    in any string derived from A.
    """
    nt = get_non_terminals(productions)
    leading = {n: set() for n in nt}
    changed = True
    while changed:
        changed = False
        for n, prods in productions.items():
            for prod in prods:
                for sym in prod:
                    if sym not in nt:
                        if sym not in leading[n]:
                            leading[n].add(sym); changed = True
                        break
                    else:
                        before = len(leading[n])
                        leading[n] |= leading[sym]
                        if len(leading[n]) != before: changed = True
                        break   # no ε — stop after first symbol
    return leading


def compute_trailing(productions):
    """
    TRAILING(A) = set of terminals that can be the last terminal
    in any string derived from A.
    """
    nt = get_non_terminals(productions)
    trailing = {n: set() for n in nt}
    changed = True
    while changed:
        changed = False
        for n, prods in productions.items():
            for prod in prods:
                for sym in reversed(prod):
                    if sym not in nt:
                        if sym not in trailing[n]:
                            trailing[n].add(sym); changed = True
                        break
                    else:
                        before = len(trailing[n])
                        trailing[n] |= trailing[sym]
                        if len(trailing[n]) != before: changed = True
                        break
    return trailing


def build_precedence_table(productions):
    """
    Build the Operator Precedence Relation Table.

    Three standard rules (Floyd 1963):
      R1 : a =· b   if  A→…a b…  or  A→…a B b…
      R2 : a <· b   if  A→…a B…  and b ∈ LEADING(B)
      R3 : a ·> b   if  A→…B b…  and a ∈ TRAILING(B)

    Plus boundary rules for '$':
      $ <· t  for every terminal t  ($ always yields to incoming tokens)
      t ·> $  for every t ∈ TRAILING(start)
      $ =· $  (accept condition)

    Setting $ <· t for ALL terminals (not just LEADING of start) is the
    correct textbook behaviour: from the bottom-of-stack marker, any
    token that can legally appear should be shifted.
    """
    nt       = get_non_terminals(productions)
    operators = extract_operators(productions)
    leading  = compute_leading(productions)
    trailing = compute_trailing(productions)
    start    = list(productions.keys())[0]
    table    = {}

    def set_rel(a, b, rel):
        """=· takes priority; otherwise first-come wins."""
        if (a, b) in table:
            if table[(a, b)] == '=·': return
            if rel == '=·':           table[(a, b)] = rel
        else:
            table[(a, b)] = rel

    for n, prods in productions.items():
        for prod in prods:
            for i, a in enumerate(prod):
                # R1a : a =· b  (adjacent terminals)
                if i+1 < len(prod):
                    b = prod[i+1]
                    if a not in nt and b not in nt:
                        set_rel(a, b, '=·')

                # R1b : a =· b  (terminal – NT – terminal)
                if i+2 < len(prod):
                    B, b = prod[i+1], prod[i+2]
                    if a not in nt and B in nt and b not in nt:
                        set_rel(a, b, '=·')

                # R2 : a <· LEADING(B)
                if i+1 < len(prod):
                    B = prod[i+1]
                    if a not in nt and B in nt:
                        for lead in leading.get(B, []):
                            set_rel(a, lead, '<·')

                # R3 : TRAILING(B) ·> b
                if i+1 < len(prod):
                    b = prod[i+1]
                    if a in nt and b not in nt:
                        for trail in trailing.get(a, []):
                            set_rel(trail, b, '·>')

    # Heuristic precedence chain for the bundled arithmetic-style grammar.
    # If the start rule lists binary operator productions in order, later
    # operators bind tighter than earlier ones.
    inferred_ops = []
    for prod in productions.get(start, []):
        if len(prod) == 3 and prod[0] in nt and prod[1] not in nt and prod[2] in nt:
            op = prod[1]
            if op not in inferred_ops:
                inferred_ops.append(op)

    for i, lower in enumerate(inferred_ops):
        set_rel(lower, lower, '·>')
        for higher in inferred_ops[i+1:]:
            set_rel(lower, higher, '<·')
            set_rel(higher, lower, '·>')

    # ── $ boundary rules ──────────────────────────────────────────
    # $ <· every non-$ terminal (standard: $ always shifts valid tokens)
    for op in operators:
        if op != '$':
            set_rel('$', op, '<·')

    # TRAILING(start) ·> $
    for trail in trailing.get(start, []):
        set_rel(trail, '$', '·>')

    # End-of-input must trigger reductions from any terminal still on stack.
    for op in operators:
        if op != '$':
            set_rel(op, '$', '·>')

    # $ =· $ (accept)
    set_rel('$', '$', '=·')

    return table, operators


# ══════════════════════════════════════════════════════════════
#  MODULE 3 — PARSING ENGINE
# ══════════════════════════════════════════════════════════════

def tokenize_input(input_str, operators, non_terminals):
    """Tokenize the input expression; validate each token."""
    valid  = set(operators) - {'$'}
    tokens, errors = [], []
    for part in input_str.strip().split():
        for s in tokenize_rhs(part):
            if s in valid or re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', s):
                tokens.append(s)
            else:
                errors.append(f"Unknown token: '{s}'")
    return (None, errors) if errors else (tokens, [])


def parse_with_operator_precedence(input_tokens, prec_table, productions):
    """
    Classic Floyd Operator-Precedence parsing algorithm.

    Stack holds terminals and non-terminals.
    Only terminals are compared via the precedence table.
    top_terminal() returns the highest terminal on the stack.

    Shift  when top_terminal <· or =· current input token.
    Reduce when top_terminal ·> current input token:
       pop symbols until the terminal BELOW the handle has <· to the
       leftmost terminal of the handle.
    Accept when stack = ['$', NT] and current input = '$'.
    """
    nt    = get_non_terminals(productions)
    start = list(productions.keys())[0]

    def make_node(label, children=None):
        return {"label": label, "children": list(children or [])}

    def top_terminal(stk):
        for s in reversed(stk):
            if s not in nt: return s
        return '$'

    def find_production(handle):
        """Match handle to a grammar rule; return the LHS."""
        # Exact match
        for n, prods in productions.items():
            for prod in prods:
                if prod == handle: return n
        # Operator-skeleton match (ignore NT positions)
        for n, prods in productions.items():
            for prod in prods:
                if len(prod) != len(handle): continue
                if all(ph == pp or (ph in nt and pp in nt)
                       for ph, pp in zip(handle, prod)):
                    return n
        return None

    stack = ['$']
    node_stack = [None]
    inp   = input_tokens + ['$']
    idx   = 0
    steps = []

    for _ in range(400):
        top_t = top_terminal(stack)
        cur   = inp[idx]
        st    = ' '.join(stack)
        it    = ' '.join(inp[idx:])

        # ── Accept ────────────────────────────────────────────────
        if (cur == '$' and len(stack) == 2
                and stack[0] == '$' and stack[1] in nt):
            steps.append((st, it, "✅  ACCEPT"))
            return steps, "Accepted", node_stack[1]

        rel = prec_table.get((top_t, cur))

        if rel is None:
            steps.append((st, it,
                f"ERROR: no relation defined for ({top_t}, {cur})"))
            return steps, "Rejected", None

        # ── Shift ─────────────────────────────────────────────────
        if rel in ('<·', '=·'):
            steps.append((st, it,
                f"Shift  '{cur}'   [{top_t} {rel} {cur}]"))
            stack.append(cur)
            node_stack.append(make_node(cur))
            idx += 1

        # ── Reduce ────────────────────────────────────────────────
        else:   # '·>'
            right_idx = next((i for i in range(len(stack) - 1, -1, -1)
                              if stack[i] not in nt), None)
            if right_idx is None:
                steps.append((st, it, "ERROR: no terminal found on stack"))
                return steps, "Rejected", None

            boundary_idx = None
            right_t = stack[right_idx]
            for pos in range(right_idx - 1, -1, -1):
                sym = stack[pos]
                if sym in nt:
                    continue
                below = prec_table.get((sym, right_t))
                if below in ('<·', '=·'):
                    boundary_idx = pos
                    break

            if boundary_idx is None:
                steps.append((st, it,
                    f"ERROR: could not locate reduction boundary for {right_t}"))
                return steps, "Rejected", None

            handle = stack[boundary_idx + 1:]
            handle_nodes = node_stack[boundary_idx + 1:]
            del stack[boundary_idx + 1:]
            del node_stack[boundary_idx + 1:]

            matched = find_production(handle)
            if matched is None:
                steps.append((st, it,
                    f"ERROR: no production matches handle '{' '.join(handle)}'"))
                return steps, "Rejected", None
            steps.append((st, it,
                f"Reduce '{' '.join(handle)}'  →  {matched}"))
            stack.append(matched)
            node_stack.append(make_node(matched, handle_nodes))

    steps.append(("", "", "ERROR: exceeded maximum steps"))
    return steps, "Rejected", None


# ══════════════════════════════════════════════════════════════
#  MODULE 4 — GUI LAYER
# ══════════════════════════════════════════════════════════════

class App:
    # ── Palette ───────────────────────────────────────────────
    BG        = "#1a1d2e"
    PANEL     = "#252840"
    ACCENT    = "#ff8a3d"
    ACCENT2   = "#50e3c2"
    TEXT      = "#e8e8f0"
    TEXT_DIM  = "#8a8aa8"
    SUCCESS   = "#4cde8a"
    FAIL      = "#ff5f6d"
    TBL_HDR   = "#2e3150"
    ROW_A     = "#1f2238"
    ROW_B     = "#252840"
    BORDER    = "#3a3d5c"

    F_TITLE  = ("Courier New", 17, "bold")
    F_LABEL  = ("Courier New", 10, "bold")
    F_MONO   = ("Courier New", 10)
    F_SMALL  = ("Courier New", 9)
    F_RESULT = ("Courier New", 14, "bold")

    def __init__(self, root):
        self.root = root
        root.title("Operator Precedence Parser")
        root.configure(bg=self.BG)
        root.geometry("1180x800")
        root.minsize(920, 620)
        self._build_ui()

    # ── Top-level layout ─────────────────────────────────────

    def _build_ui(self):
        tk.Frame(self.root, bg=self.ACCENT, height=4).pack(fill="x")

        hdr = tk.Frame(self.root, bg=self.BG, pady=12)
        hdr.pack(fill="x", padx=24)
        tk.Label(hdr, text="⊢  Operator Precedence Parser",
                 font=self.F_TITLE, bg=self.BG, fg=self.ACCENT).pack(side="left")
        tk.Label(hdr, text="Compiler Construction",
             font=self.F_SMALL, bg=self.BG, fg=self.TEXT_DIM).pack(side="right")

        tk.Frame(self.root, bg=self.BORDER, height=1).pack(fill="x", padx=24)

        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill="both", expand=True, padx=24, pady=10)

        left = tk.Frame(body, bg=self.BG, width=340)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        self._build_left(left)

        right = tk.Frame(body, bg=self.BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_right(right)

    # ── Left panel ───────────────────────────────────────────

    def _sep(self, parent, label=""):
        tk.Frame(parent, bg=self.BORDER, height=1).pack(fill="x", pady=(12, 3))
        if label:
            tk.Label(parent, text=label, font=self.F_LABEL,
                     bg=self.BG, fg=self.ACCENT2).pack(anchor="w")

    def _entry_style(self):
        return dict(bg=self.PANEL, fg=self.TEXT,
                    insertbackground=self.ACCENT, relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=self.BORDER,
                    highlightcolor=self.ACCENT)

    def _build_left(self, p):
        tk.Label(p, text="INPUTS", font=("Courier New", 11, "bold"),
                 bg=self.BG, fg=self.TEXT_DIM).pack(anchor="w")

        self._sep(p, "① Context-Free Grammar")
        tk.Label(p, text="One rule per line:  E -> E + E | E - E | E * E | E / E | id",
                 font=self.F_SMALL, bg=self.BG, fg=self.TEXT_DIM).pack(anchor="w")
        self.cfg_text = tk.Text(p, height=7, font=self.F_MONO,
                                padx=8, pady=6, **self._entry_style())
        self.cfg_text.pack(fill="x", pady=(4, 0))
        self.cfg_text.insert("1.0", "E -> E + E | E - E | E * E | E / E | ( E ) | id")

        self._sep(p, "② Input String")
        tk.Label(p, text="Space-separated tokens",
                 font=self.F_SMALL, bg=self.BG, fg=self.TEXT_DIM).pack(anchor="w")
        self.input_var = tk.StringVar(value="id + id * id - id / id")
        tk.Entry(p, textvariable=self.input_var,
                 font=self.F_MONO, **self._entry_style()
                 ).pack(fill="x", pady=(4, 0), ipady=6)

        self._sep(p)
        tk.Button(p, text="▶   PARSE",
                  font=("Courier New", 11, "bold"),
                  bg=self.ACCENT, fg="white",
                  activebackground="#6255d4", activeforeground="white",
                  relief="flat", cursor="hand2",
                  command=self._run).pack(fill="x", ipady=10, pady=(4, 0))
        tk.Button(p, text="📂   Load .txt",
                  font=self.F_SMALL, bg=self.PANEL, fg=self.TEXT_DIM,
                  activebackground=self.BORDER, relief="flat", cursor="hand2",
                  command=self._load_cfg_from_file).pack(fill="x", ipady=4, pady=(6, 0))
        tk.Button(p, text="✕   Clear",
                  font=self.F_SMALL, bg=self.PANEL, fg=self.TEXT_DIM,
                  activebackground=self.BORDER, relief="flat", cursor="hand2",
                  command=self._clear).pack(fill="x", ipady=4, pady=(6, 0))

        self._sep(p, "③ Result")
        self.result_var = tk.StringVar(value="—")
        self.result_lbl = tk.Label(p, textvariable=self.result_var,
                                   font=self.F_RESULT, bg=self.PANEL,
                                   fg=self.TEXT, pady=14,
                                   highlightthickness=1,
                                   highlightbackground=self.BORDER)
        self.result_lbl.pack(fill="x", pady=(4, 0))

        self._sep(p, "④ Developed By")
        self.credit_box = tk.Frame(p, bg=self.PANEL,
                       highlightthickness=1,
                       highlightbackground=self.BORDER)
        self.credit_box.pack(fill="x", pady=(4, 0))
        tk.Label(self.credit_box, text="Developed by:\nMuhammad Isbah\nChahat Fatima",
             font=self.F_LABEL, bg=self.PANEL, fg=self.TEXT,
             justify="center", pady=14).pack(fill="x")

        self.log_box = tk.Text(p, height=5, font=self.F_SMALL,
                               state="disabled", padx=6, pady=4,
                               **self._entry_style())
        self.log_box.pack_forget()

    # ── Right panel (notebook) ───────────────────────────────

    def _build_right(self, p):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.PANEL,
                        foreground=self.TEXT_DIM,
                        font=("Courier New", 10, "bold"), padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", self.ACCENT)],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(p)
        nb.pack(fill="both", expand=True)

        t1 = tk.Frame(nb, bg=self.BG); nb.add(t1, text="  Parsing Steps  ")
        t2 = tk.Frame(nb, bg=self.BG); nb.add(t2, text="  Precedence Table  ")
        t3 = tk.Frame(nb, bg=self.BG); nb.add(t3, text="  Grammar Info  ")
        t4 = tk.Frame(nb, bg=self.BG); nb.add(t4, text="  Parse Tree  ")

        self._build_steps_tab(t1)
        self._build_prec_tab(t2)
        self._build_grammar_tab(t3)
        self._build_tree_tab(t4)

    def _build_steps_tab(self, p):
        tk.Label(p, text="Step-by-Step Parse Trace",
                 font=self.F_LABEL, bg=self.BG,
                 fg=self.TEXT_DIM).pack(anchor="w", padx=8, pady=(8, 4))

        frm = tk.Frame(p, bg=self.BG)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        style = ttk.Style()
        style.configure("Treeview",
                        background=self.ROW_A, foreground=self.TEXT,
                        fieldbackground=self.ROW_A, font=self.F_MONO,
                        rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading",
                        background=self.TBL_HDR, foreground=self.ACCENT2,
                        font=("Courier New", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", self.ACCENT)])

        cols = ("Step", "Stack", "Input", "Action")
        self.tree = ttk.Treeview(frm, columns=cols,
                                  show="headings", selectmode="browse")
        for col, w in zip(cols, [50, 230, 200, 400]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")

        self.tree.tag_configure("odd",    background=self.ROW_A)
        self.tree.tag_configure("even",   background=self.ROW_B)
        self.tree.tag_configure("accept", background="#1a3d2b", foreground=self.SUCCESS)
        self.tree.tag_configure("err",    background="#3d1a1a", foreground=self.FAIL)

        vsb = ttk.Scrollbar(frm, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1); frm.columnconfigure(0, weight=1)

    def _build_prec_tab(self, p):
        tk.Label(p,
                 text="<· = yields (shift)   ·> = takes (reduce)   =· = equal",
                 font=self.F_SMALL, bg=self.BG,
                 fg=self.TEXT_DIM).pack(anchor="w", padx=8, pady=(8, 4))

        frm = tk.Frame(p, bg=self.BG)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.prec_canvas = tk.Canvas(frm, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(frm, orient="vertical",
                            command=self.prec_canvas.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal",
                            command=self.prec_canvas.xview)
        self.prec_canvas.configure(yscrollcommand=vsb.set,
                                    xscrollcommand=hsb.set)
        self.prec_canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1); frm.columnconfigure(0, weight=1)

        self.prec_inner = tk.Frame(self.prec_canvas, bg=self.BG)
        self.prec_canvas.create_window((0, 0), window=self.prec_inner,
                                        anchor="nw")
        self.prec_inner.bind("<Configure>", lambda e:
            self.prec_canvas.configure(
                scrollregion=self.prec_canvas.bbox("all")))

    def _build_grammar_tab(self, p):
        self.grammar_box = scrolledtext.ScrolledText(
            p, font=self.F_MONO, bg=self.PANEL, fg=self.TEXT,
            relief="flat", bd=0, padx=10, pady=8, state="disabled",
            highlightthickness=1, highlightbackground=self.BORDER)
        self.grammar_box.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tree_tab(self, p):
        tk.Label(p, text="Parse Tree for the accepted input",
                 font=self.F_LABEL, bg=self.BG,
                 fg=self.TEXT_DIM).pack(anchor="w", padx=8, pady=(8, 4))

        frm = tk.Frame(p, bg=self.BG)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree_canvas = tk.Canvas(frm, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree_canvas.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self.tree_canvas.xview)
        self.tree_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree_canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        self.tree_canvas.create_text(
            20, 20, anchor="nw", fill=self.TEXT_DIM,
            font=self.F_MONO, text="Parse tree will appear here after a successful parse.")

    # ── Event handlers ───────────────────────────────────────

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _load_cfg_from_file(self):
        file_path = filedialog.askopenfilename(
            title="Open CFG text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception as exc:
            messagebox.showerror("File Error", f"Could not read file:\n{exc}")
            return

        grammar_text, input_text = extract_cfg_and_input_from_text(content)
        if grammar_text:
            self.cfg_text.delete("1.0", "end")
            self.cfg_text.insert("1.0", grammar_text)
        if input_text:
            self.input_var.set(input_text)

        self._log(f"Loaded grammar from {os.path.basename(file_path)}")

    def _clear(self):
        self.tree.delete(*self.tree.get_children())
        for w in self.prec_inner.winfo_children(): w.destroy()
        if hasattr(self, "tree_canvas"):
            self.tree_canvas.delete("all")
            self.tree_canvas.create_text(
                20, 20, anchor="nw", fill=self.TEXT_DIM,
                font=self.F_MONO,
                text="Parse tree will appear here after a successful parse.")
        for box in (self.grammar_box, self.log_box):
            box.configure(state="normal"); box.delete("1.0","end")
            box.configure(state="disabled")
        self.result_var.set("—")
        self.result_lbl.configure(fg=self.TEXT)

    def _run(self):
        self._clear()
        self._log("Starting parse…")

        # 1. Parse CFG
        productions, errs = parse_cfg(self.cfg_text.get("1.0","end"))
        if errs:
            [self._log("CFG ERR: " + e) for e in errs]
            messagebox.showerror("CFG Error", "\n".join(errs)); return
        self._log(f"✓ Grammar OK — {len(productions)} non-terminal(s)")
        self._show_grammar(productions)

        # 2. Build table
        try:
            prec_table, operators = build_precedence_table(productions)
        except Exception as ex:
            self._log(f"Table error: {ex}")
            messagebox.showerror("Error", str(ex)); return
        self._log(f"✓ Precedence table built — {len(operators)} operator(s)")
        self._show_prec_table(prec_table, operators)

        # 3. Tokenise input
        nt = get_non_terminals(productions)
        tokens, errs = tokenize_input(self.input_var.get(), operators, nt)
        if errs:
            [self._log("TOKEN ERR: " + e) for e in errs]
            messagebox.showerror("Token Error", "\n".join(errs)); return
        self._log(f"✓ Tokens: {tokens}")

        # 4. Parse
        try:
            steps, result, parse_tree = parse_with_operator_precedence(
                tokens, prec_table, productions)
        except Exception as ex:
            self._log(f"Parse error: {ex}")
            messagebox.showerror("Parse Error", str(ex)); return

        # 5. Display
        self._show_steps(steps)
        if result == "Accepted":
            self.result_var.set("✅   ACCEPTED")
            self.result_lbl.configure(fg=self.SUCCESS)
            self._log(f"✓ ACCEPTED in {len(steps)} step(s)")
            self._show_parse_tree(parse_tree)
        else:
            self.result_var.set("❌   REJECTED")
            self.result_lbl.configure(fg=self.FAIL)
            self._log(f"✗ REJECTED after {len(steps)} step(s)")
            self._show_parse_tree(None)

    def _show_steps(self, steps):
        self.tree.delete(*self.tree.get_children())
        for i, (stk, inp, act) in enumerate(steps):
            tag = ("accept" if "ACCEPT" in act else
                   "err"    if "ERROR"  in act else
                   "even"   if i % 2 == 0 else "odd")
            self.tree.insert("", "end",
                values=(i+1, stk, inp, act), tags=(tag,))

    def _show_prec_table(self, prec_table, operators):
        for w in self.prec_inner.winfo_children(): w.destroy()

        def cell(txt, row, col, bg, fg, bold=False):
            fnt = ("Courier New", 9, "bold") if bold else ("Courier New", 9)
            tk.Label(self.prec_inner, text=txt, font=fnt,
                     bg=bg, fg=fg, width=7, relief="flat", bd=1
                     ).grid(row=row, column=col, padx=1, pady=1, ipady=5)

        cell("a \\ b", 0, 0, self.TBL_HDR, self.ACCENT2, bold=True)
        for j, op in enumerate(operators):
            cell(op, 0, j+1, self.TBL_HDR, self.ACCENT2, bold=True)

        for i, op1 in enumerate(operators):
            bg_row = self.ROW_A if i % 2 == 0 else self.ROW_B
            cell(op1, i+1, 0, self.TBL_HDR, self.ACCENT2, bold=True)
            for j, op2 in enumerate(operators):
                rel = prec_table.get((op1, op2), "")
                fg  = (self.TEXT_DIM if not rel else
                       "#7ec8e3"     if rel == '<·' else
                       self.FAIL     if rel == '·>' else
                       self.SUCCESS)
                cell(rel or "·", i+1, j+1, bg_row, fg)

    def _show_grammar(self, productions):
        leading  = compute_leading(productions)
        trailing = compute_trailing(productions)
        ops      = extract_operators(productions)
        lines = [
            "═"*54, "  GRAMMAR SUMMARY", "═"*54,
            f"  Start Symbol : {list(productions.keys())[0]}",
            f"  Non-Terminals: {', '.join(productions.keys())}",
            f"  Terminals     : {', '.join(ops)}", "",
            "  PRODUCTIONS:",
        ]
        for nt, prods in productions.items():
            for prod in prods:
                lines.append(f"    {nt}  →  {' '.join(prod)}")
        lines += ["", "  LEADING SETS:"]
        for nt, s in leading.items():
            lines.append(f"    LEADING({nt})  = {{ {', '.join(sorted(s))} }}")
        lines += ["", "  TRAILING SETS:"]
        for nt, s in trailing.items():
            lines.append(f"    TRAILING({nt}) = {{ {', '.join(sorted(s))} }}")
        lines.append("═"*54)

        self.grammar_box.configure(state="normal")
        self.grammar_box.delete("1.0", "end")
        self.grammar_box.insert("end", "\n".join(lines))
        self.grammar_box.configure(state="disabled")

    def _show_parse_tree(self, root):
        self.tree_canvas.delete("all")

        if not root:
            self.tree_canvas.create_text(
                20, 20, anchor="nw", fill=self.TEXT_DIM,
                font=self.F_MONO,
                text="No parse tree available for a rejected parse.")
            return

        def leaf_count(node):
            children = node.get("children", [])
            if not children:
                return 1
            return sum(leaf_count(child) for child in children)

        def max_depth(node):
            children = node.get("children", [])
            if not children:
                return 1
            return 1 + max(max_depth(child) for child in children)

        positions = {}
        next_leaf = [0]

        def assign(node, depth):
            children = node.get("children", [])
            if not children:
                x = next_leaf[0]
                positions[id(node)] = (x, depth)
                next_leaf[0] += 1
                return x

            child_xs = [assign(child, depth + 1) for child in children]
            x = (child_xs[0] + child_xs[-1]) / 2
            positions[id(node)] = (x, depth)
            return x

        assign(root, 0)
        leaves = max(1, leaf_count(root))
        depth = max_depth(root)
        x_gap = 120
        y_gap = 90
        x_margin = 40
        y_margin = 40
        canvas_width = max(600, x_margin * 2 + (leaves - 1) * x_gap + 120)
        canvas_height = max(420, y_margin * 2 + (depth - 1) * y_gap + 120)
        self.tree_canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))

        def draw(node):
            x_idx, level = positions[id(node)]
            x = x_margin + x_idx * x_gap
            y = y_margin + level * y_gap
            label = node.get("label", "")
            box_w = max(48, 14 + len(label) * 8)
            box_h = 28
            fill = self.ACCENT if node.get("children") else self.PANEL
            outline = self.ACCENT2 if node.get("children") else self.BORDER
            self.tree_canvas.create_rectangle(
                x - box_w // 2, y - box_h // 2, x + box_w // 2, y + box_h // 2,
                fill=fill, outline=outline, width=2)
            self.tree_canvas.create_text(
                x, y, text=label, fill=self.TEXT, font=self.F_MONO)

            for child in node.get("children", []):
                child_x_idx, child_level = positions[id(child)]
                child_x = x_margin + child_x_idx * x_gap
                child_y = y_margin + child_level * y_gap
                self.tree_canvas.create_line(
                    x, y + box_h // 2, child_x, child_y - box_h // 2,
                    fill=self.TEXT_DIM, width=2)
                draw(child)

        draw(root)


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()