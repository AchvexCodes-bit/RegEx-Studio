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
        with self.assertRaises(RegexSyntaxError):
            parse("café")


    def test_outer_anchors_in_full_match_mode(self):
        self.assertTrue(self.matches(r"^(ab|c)+\d{2}$", "abc12"))
        self.assertFalse(self.matches(r"^(ab|c)+\d{2}$", "abc1"))


    def test_escaped_dollar_remains_literal(self):
        self.assertTrue(self.matches(r"\$", "$"))
        self.assertFalse(self.matches(r"\$", "x"))

if __name__=="__main__": unittest.main()
