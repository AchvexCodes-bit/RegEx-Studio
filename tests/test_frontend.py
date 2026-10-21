import re
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HTML_PATH = Path(__file__).resolve().parents[1] / "index.html"
HTML = HTML_PATH.read_text(encoding="utf-8")


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []

    def handle_starttag(self, tag, attrs):
        value = dict(attrs).get("id")
        if value:
            self.ids.append(value)


class FrontendSmokeTests(unittest.TestCase):
    def setUp(self):
        self.parser = IdParser()
        self.parser.feed(HTML)

    def test_dom_ids_are_unique(self):
        duplicates = {value for value in self.parser.ids if self.parser.ids.count(value) > 1}
        self.assertEqual(duplicates, set())

    def test_literal_javascript_id_references_exist(self):
        known_ids = set(self.parser.ids)
        references = set(re.findall(r'\$\("([^"]+)"\)', HTML))
        self.assertTrue(references)
        self.assertEqual(references - known_ids, set())

    def test_user_workspace_and_authentication_controls_exist(self):
        ids = set(self.parser.ids)
        expected = {
            "accountDialog", "accountForm", "accountOpen", "logoutButton",
            "userWorkspace", "savedName", "savePattern", "patternSearch",
            "favoritesOnly", "savedList", "workspaceStatus",
        }
        self.assertTrue(expected.issubset(ids))

    def test_accessibility_and_edge_case_fixes_remain_present(self):
        for marker in ("prefers-reduced-motion", "IntersectionObserver", "traceMatched", 'title="Zero-width match"'):
            with self.subTest(marker=marker):
                self.assertIn(marker, HTML)

    def test_saved_user_content_is_rendered_as_text(self):
        self.assertIn("title.textContent=item.name", HTML)
        self.assertIn('code.textContent="/"+item.pattern+"/"+item.flags', HTML)
        self.assertNotIn('card.innerHTML=', HTML)

    def test_inline_javascript_syntax_when_node_is_available(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed; CI installs it and runs scripts/check_frontend.py")
        scripts = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script\s*>", HTML, re.I)
        self.assertTrue(scripts)
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as temp:
            temp.write("\n;\n".join(scripts))
            filename = temp.name
        try:
            result = subprocess.run([node, "--check", filename], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            Path(filename).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
