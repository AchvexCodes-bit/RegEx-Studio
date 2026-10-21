import json
from django.test import SimpleTestCase, Client

class ApiTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()
    def test_home_serves_workspace(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RegEx Studio", response.content)
    def test_health(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
    def test_compile_returns_ast_and_automata(self):
        response = self.client.post("/api/v1/automata/compile/", data=json.dumps({"pattern": "(ab|c)+\\d{2}"}), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertIn("ast", data)
        self.assertIn("nfa", data)
        self.assertGreater(data["dfa"]["states"], 0)
        self.assertGreater(data["minimized_dfa"]["states"], 0)
    def test_simulation_trace(self):
        response = self.client.post("/api/v1/automata/simulate/", data=json.dumps({"pattern": "(ab|c)+\\d{2}", "input": "abc12"}), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["matched"])
        self.assertEqual(len(data["trace"]), 6)
    def test_invalid_pattern_has_position(self):
        response = self.client.post("/api/v1/automata/compile/", data=json.dumps({"pattern": "("}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("position", response.json())
    def test_oversized_compile_request_returns_413(self):
        response = self.client.post("/api/v1/automata/compile/", data=" " * 17000, content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertIn("16 KB", response.json()["error"])

    def test_oversized_simulation_request_returns_413(self):
        response = self.client.post("/api/v1/automata/simulate/", data=" " * 17000, content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertIn("16 KB", response.json()["error"])

    def test_non_object_json_returns_400(self):
        response = self.client.post("/api/v1/automata/compile/", data=json.dumps(["not", "an", "object"]), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("JSON body must be an object", response.json()["error"])
