import unittest
from engine.regex_engine import parse, NFA, to_dfa, minimize_dfa, compile_pattern, RegexSyntaxError

class EngineTests(unittest.TestCase):
    def matches(self, pattern, text):
        nfa=NFA().compile(parse(pattern))
        return nfa.simulate(text)["matched"]
    def test_literals_and_full_match(self):
        self.assertTrue(self.matches("abc","abc"))
        self.assertFalse(self.matches("abc","zabc"))
    def test_alternation_and_repetition(self):
        for text in ("ab","c","abcab"): self.assertTrue(self.matches("(ab|c)+",text))
        self.assertFalse(self.matches("(ab|c)+","a"))
    def test_classes_and_bounds(self):
        self.assertTrue(self.matches("[a-c]{2,3}","abc"))
        self.assertFalse(self.matches("[a-c]{2,3}","abcd"))
        self.assertTrue(self.matches(r"\d+","123"))
    def test_empty_and_optional(self):
        self.assertTrue(self.matches("a*",""))
        self.assertTrue(self.matches("colou?r","color"))
    def test_bad_patterns(self):
        for p in ("(","[abc","a{4,2}","*a", "\\"):
            with self.assertRaises(RegexSyntaxError): parse(p)
    def test_dfa_minimization_preserves_examples(self):
        c=compile_pattern("(ab|c)+")
        d,m=c["dfa"],c["minimized"]
        for word in ("","a","ab","c","abc","cc","ac"):
            s=d["start"]
            for ch in word: s=d["transitions"].get(s,{}).get(ch,-1)
            one=s in d["accepts"]
            s=m["start"]
            for ch in word: s=m["transitions"].get(s,{}).get(ch,-1)
            two=s in m["accepts"]
            self.assertEqual(one,two,word)


    def test_nfa_dfa_minimized_equivalence_on_generated_strings(self):
        from itertools import product
        for pattern in ("a*", "(ab|c)+", "[a-c]{2,3}", "a?b"):
            compiled = compile_pattern(pattern)
            nfa, dfa, minimized = compiled["nfa"], compiled["dfa"], compiled["minimized"]
            for length in range(5):
                for chars in product("abc12", repeat=length):
                    sample = "".join(chars)
                    expected = nfa.simulate(sample)["matched"]
                    def accepts(machine):
                        state = machine["start"]
                        for char in sample:
                            state = machine["transitions"].get(state, {}).get(char, -1)
                        return state in machine["accepts"]
                    self.assertEqual(accepts(dfa), expected, (pattern, sample, "DFA"))
                    self.assertEqual(accepts(minimized), expected, (pattern, sample, "minimized DFA"))


    def test_non_ascii_pattern_is_rejected_explicitly(self):
        for pattern in ("café", "[\\é]"):
            with self.subTest(pattern=pattern), self.assertRaises(RegexSyntaxError):
                parse(pattern)


    def test_outer_anchors_in_full_match_mode(self):
        self.assertTrue(self.matches(r"^(ab|c)+\d{2}$", "abc12"))
        self.assertFalse(self.matches(r"^(ab|c)+\d{2}$", "abc1"))


    def test_escaped_dollar_remains_literal(self):
        self.assertTrue(self.matches(r"\$", "$"))
        self.assertFalse(self.matches(r"\$", "x"))


    def test_every_bounded_quantifier_form(self):
        for pattern, accepted, rejected in [
            ("a{2}", ("aa",), ("", "a", "aaa")),
            ("a{2,}", ("aa", "aaa", "aaaa"), ("", "a")),
            ("a{0,2}", ("", "a", "aa"), ("aaa",)),
            ("a{0}", ("",), ("a",)),
            ("a{1,3}", ("a", "aa", "aaa"), ("", "aaaa")),
        ]:
            with self.subTest(pattern=pattern):
                for sample in accepted:
                    self.assertTrue(self.matches(pattern, sample), (pattern, sample))
                for sample in rejected:
                    self.assertFalse(self.matches(pattern, sample), (pattern, sample))

    def test_character_class_negation_ranges_and_escapes(self):
        self.assertTrue(self.matches("[^0-9]+", "abc_"))
        self.assertFalse(self.matches("[^0-9]+", "abc1"))
        self.assertTrue(self.matches(r"\D+", "abc"))
        self.assertFalse(self.matches(r"\D+", "ab3"))
        self.assertTrue(self.matches(r"\W+", "---"))
        self.assertFalse(self.matches(r"\W+", "a-"))
        self.assertTrue(self.matches(r"\.", "."))
        self.assertTrue(self.matches(r"[a-c]+", "abc"))
        with self.assertRaises(RegexSyntaxError):
            parse("[z-a]")

    def test_dot_excludes_line_breaks_and_empty_branches_work(self):
        self.assertTrue(self.matches(".", "x"))
        self.assertFalse(self.matches(".", "\n"))
        self.assertFalse(self.matches(".*", "a\nb"))
        self.assertTrue(self.matches("(a|)", ""))
        self.assertTrue(self.matches("(a|)", "a"))
        self.assertFalse(self.matches("(a|)", "b"))

    def test_malformed_and_nested_quantifiers_are_rejected(self):
        for pattern in ("a**", "a{", "a{,2}", "a{1,2", "a{3,2}", "[z-a]", "\\"):
            with self.subTest(pattern=pattern), self.assertRaises(RegexSyntaxError):
                parse(pattern)

    def test_engine_resource_limits(self):
        with self.assertRaises(RegexSyntaxError):
            parse("a" * 513)
        with self.assertRaises(RegexSyntaxError):
            parse("a{33}")
        machine = NFA().compile(parse("a"))
        with self.assertRaises(ValueError):
            machine.simulate("x" * 4097)

    def test_ast_graph_and_trace_shapes(self):
        compiled = compile_pattern("a(b|c)")
        ast = compiled["ast"]
        self.assertEqual(ast.kind, "concat")
        from engine.regex_engine import ast_json, graph_json
        ast_data = ast_json(ast)
        graph_data = graph_json(compiled["nfa"])
        self.assertEqual(ast_data["type"], "concat")
        self.assertGreaterEqual(len(graph_data["states"]), 2)
        self.assertEqual(graph_data["start"], compiled["nfa"].start)
        self.assertEqual(graph_data["accept"], compiled["nfa"].accept)
        result = compiled["nfa"].simulate("ab")
        self.assertTrue(result["matched"])
        self.assertEqual(len(result["trace"]), 3)
        self.assertEqual(result["trace"][0]["index"], 0)
        self.assertEqual(result["trace"][-1]["index"], 2)

    def test_nfa_dfa_and_minimized_equivalence_for_more_grammars(self):
        from itertools import product
        patterns = (
            "", "a", "a*", "a+", "a?", "a{0,2}", "(a|b)c",
            "[a-c]{1,2}", r"\d+", r"\w*", "[^0-9]+", r"\.",
        )
        for pattern in patterns:
            compiled = compile_pattern(pattern)
            for length in range(4):
                for chars in product("ab1.", repeat=length):
                    sample = "".join(chars)
                    expected = compiled["nfa"].simulate(sample)["matched"]
                    for machine_name in ("dfa", "minimized"):
                        machine = compiled[machine_name]
                        state = machine["start"]
                        for char in sample:
                            state = machine["transitions"].get(state, {}).get(char, -1)
                        self.assertEqual(state in machine["accepts"], expected, (pattern, sample, machine_name))

if __name__=="__main__": unittest.main()
