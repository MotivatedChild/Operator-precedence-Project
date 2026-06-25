import unittest

from operator_precedence_parser import extract_cfg_and_input_from_text


class ExtractCfgAndInputTests(unittest.TestCase):
    def test_extracts_grammar_and_input_from_separated_file(self):
        content = """E -> E + E | E * E | id

id + id * id"""
        grammar, input_text = extract_cfg_and_input_from_text(content)
        self.assertEqual(grammar, "E -> E + E | E * E | id")
        self.assertEqual(input_text, "id + id * id")

    def test_extracts_grammar_and_input_from_labeled_sections(self):
        content = """GRAMMAR:
E -> E + E | id

INPUT:
id + id"""
        grammar, input_text = extract_cfg_and_input_from_text(content)
        self.assertEqual(grammar, "E -> E + E | id")
        self.assertEqual(input_text, "id + id")


if __name__ == "__main__":
    unittest.main()
