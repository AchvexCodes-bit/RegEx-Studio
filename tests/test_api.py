import json

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase

from playground.models import SavedPattern


class ApiTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_home_serves_workspace_and_account_ui(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = b"".join(response.streaming_content)
        self.assertIn(b"RegEx Studio", body)
        self.assertIn(b'id="userWorkspace"', body)
        self.assertIn(b'id="accountDialog"', body)

    def test_home_sets_csrf_cookie(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_health(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_compile_returns_ast_and_automata(self):
        response = self.post_json("/api/v1/automata/compile/", {"pattern": r"(ab|c)+\d{2}"})
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertIn("ast", data)
        self.assertIn("nfa", data)
        self.assertGreater(data["dfa"]["states"], 0)
        self.assertGreater(data["minimized_dfa"]["states"], 0)

    def test_compile_rejects_non_string_pattern(self):
        response = self.post_json("/api/v1/automata/compile/", {"pattern": ["not", "a", "string"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("pattern must be a string", response.json()["error"])

    def test_simulation_trace(self):
        response = self.post_json("/api/v1/automata/simulate/", {"pattern": r"(ab|c)+\d{2}", "input": "abc12"})
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["matched"])
        self.assertEqual(len(data["trace"]), 6)
        self.assertTrue(data["trace"][0]["epsilon"])
        self.assertEqual(data["trace"][-1]["index"], 5)

    def test_simulation_rejects_non_string_fields(self):
        response = self.post_json("/api/v1/automata/simulate/", {"pattern": "a", "input": 123})
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be strings", response.json()["error"])

    def test_invalid_pattern_has_position(self):
        response = self.post_json("/api/v1/automata/compile/", {"pattern": "("})
        self.assertEqual(response.status_code, 400)
        self.assertIn("position", response.json())

    def test_malformed_json_returns_400(self):
        response = self.client.post(
            "/api/v1/automata/compile/",
            data="{",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_oversized_compile_request_returns_413(self):
        response = self.client.post("/api/v1/automata/compile/", data=" " * 17000, content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertIn("16 KB", response.json()["error"])

    def test_oversized_simulation_request_returns_413(self):
        response = self.client.post("/api/v1/automata/simulate/", data=" " * 17000, content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertIn("16 KB", response.json()["error"])

    def test_non_object_json_returns_400(self):
        response = self.post_json("/api/v1/automata/compile/", ["not", "an", "object"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("JSON body must be an object", response.json()["error"])

    def test_health_requires_get(self):
        response = self.client.post("/api/v1/health/")
        self.assertEqual(response.status_code, 405)


class UserWorkspaceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="regex-user",
            email="regex@example.com",
            password="StrongTestPass123!",
        )

    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_anonymous_account_status_and_workspace_denial(self):
        status = self.client.get("/api/v1/auth/me/")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["authenticated"])
        self.assertIsNone(status.json()["user"])
        self.assertEqual(self.client.get("/api/v1/patterns/").status_code, 401)
        self.assertEqual(self.post_json("/api/v1/patterns/", {"name": "X", "pattern": "x"}).status_code, 401)

    def test_register_creates_hashed_password_and_session(self):
        response = self.post_json("/api/v1/auth/register/", {
            "username": "new-regex-user",
            "email": "new@example.com",
            "password": "CorrectHorse9!",
        })
        self.assertEqual(response.status_code, 201, response.content)
        user = self.User.objects.get(username="new-regex-user")
        self.assertTrue(user.check_password("CorrectHorse9!"))
        self.assertNotEqual(user.password, "CorrectHorse9!")
        self.assertTrue(response.json()["authenticated"])
        me = self.client.get("/api/v1/auth/me/").json()
        self.assertTrue(me["authenticated"])
        self.assertEqual(me["user"]["username"], "new-regex-user")

    def test_register_validates_username_password_and_email(self):
        cases = [
            ({"username": "", "email": "", "password": "StrongPass123"}, "Username"),
            ({"username": "short-password", "email": "", "password": "short"}, "at least 8"),
            ({"username": "bad-email", "email": "not-an-email", "password": "StrongPass123"}, "valid email"),
            ({"username": "regex-user", "email": "", "password": "StrongPass123"}, "already in use"),
            ({"username": "wrong-type", "email": "", "password": 12345678}, "must be strings"),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                response = self.post_json("/api/v1/auth/register/", payload)
                self.assertIn(response.status_code, (400, 409))
                self.assertIn(message.lower(), response.json()["error"].lower())

    def test_login_accepts_valid_credentials_and_rejects_bad_password(self):
        bad = self.post_json("/api/v1/auth/login/", {"username": "regex-user", "password": "wrong-password"})
        self.assertEqual(bad.status_code, 401)
        good = self.post_json("/api/v1/auth/login/", {"username": "regex-user", "password": "StrongTestPass123!"})
        self.assertEqual(good.status_code, 200, good.content)
        self.assertTrue(good.json()["authenticated"])
        self.assertEqual(self.client.get("/api/v1/auth/me/").json()["user"]["username"], "regex-user")

    def test_login_requires_both_fields(self):
        for payload in ({}, {"username": "regex-user"}, {"username": "", "password": "x"}):
            response = self.post_json("/api/v1/auth/login/", payload)
            self.assertEqual(response.status_code, 400)

    def test_logout_clears_authenticated_session(self):
        self.client.force_login(self.user)
        response = self.post_json("/api/v1/auth/logout/", {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertFalse(self.client.get("/api/v1/auth/me/").json()["authenticated"])

    def test_csrf_is_required_for_account_mutations(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"username": "regex-user", "password": "StrongTestPass123!"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_csrf_bootstrap_allows_protected_account_mutation(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.get("/api/v1/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        token = csrf_client.cookies["csrftoken"].value
        response = csrf_client.post(
            "/api/v1/auth/register/",
            data=json.dumps({"username": "csrf-user", "email": "", "password": "StrongPass123!"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_saved_pattern_crud_and_favorite_filter(self):
        self.client.force_login(self.user)
        payload = {
            "name": "Digits",
            "pattern": r"\d+",
            "flags": "g",
            "replacement": "[$&]",
            "test_input": "Room 123",
            "is_favorite": False,
        }
        created = self.post_json("/api/v1/patterns/", payload)
        self.assertEqual(created.status_code, 201, created.content)
        item = created.json()["pattern"]
        self.assertEqual(item["name"], "Digits")
        self.assertEqual(item["pattern"], r"\d+")
        self.assertEqual(item["replacement"], "[$&]")

        listing = self.client.get("/api/v1/patterns/").json()["patterns"]
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["id"], item["id"])

        favorited = self.client.patch(
            f"/api/v1/patterns/{item['id']}/",
            data=json.dumps({"is_favorite": True}),
            content_type="application/json",
        )
        self.assertEqual(favorited.status_code, 200, favorited.content)
        self.assertTrue(favorited.json()["pattern"]["is_favorite"])
        filtered = self.client.get("/api/v1/patterns/?favorites=1").json()["patterns"]
        self.assertEqual([value["id"] for value in filtered], [item["id"]])
        self.assertEqual(len(self.client.get("/api/v1/patterns/?q=missing").json()["patterns"]), 0)
        self.assertEqual(self.client.get("/api/v1/patterns/?q=%5Cd%2B").json()["patterns"][0]["id"], item["id"])

        renamed = self.client.patch(
            f"/api/v1/patterns/{item['id']}/",
            data=json.dumps({"name": "Room numbers"}),
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200, renamed.content)
        self.assertEqual(renamed.json()["pattern"]["name"], "Room numbers")

        deleted = self.client.delete(f"/api/v1/patterns/{item['id']}/")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])
        self.assertEqual(self.client.get("/api/v1/patterns/").json()["patterns"], [])

    def test_pattern_duplicate_name_is_case_insensitive(self):
        self.client.force_login(self.user)
        self.assertEqual(self.post_json("/api/v1/patterns/", {"name": "Email", "pattern": r".+@.+"}).status_code, 201)
        response = self.post_json("/api/v1/patterns/", {"name": "email", "pattern": r".+@.+"})
        self.assertEqual(response.status_code, 409)

    def test_pattern_rejects_bad_fields_and_limits(self):
        self.client.force_login(self.user)
        cases = [
            ({"name": "", "pattern": "x"}, "Name must"),
            ({"name": "Too long", "pattern": "x" * 513}, "512 characters"),
            ({"name": "Bad flag", "pattern": "x", "flags": "gg"}, "duplicated"),
            ({"name": "Bad flags", "pattern": "x", "flags": "uv"}, "cannot be used together"),
            ({"name": "Bad type", "pattern": "x", "is_favorite": "yes"}, "boolean"),
            ({"name": "Unknown", "pattern": "x", "unknown": "field"}, "Unknown field"),
            ({"name": "Bad sample", "pattern": "x", "test_input": "z" * 4097}, "4096 characters"),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                response = self.post_json("/api/v1/patterns/", payload)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(message.lower(), response.json()["error"].lower())

    def test_pattern_body_size_limit(self):
        self.client.force_login(self.user)
        response = self.client.post("/api/v1/patterns/", data=" " * 17000, content_type="application/json")
        self.assertEqual(response.status_code, 413)

    def test_saved_patterns_are_private_between_users(self):
        self.client.force_login(self.user)
        created = self.post_json("/api/v1/patterns/", {"name": "Private", "pattern": "secret"})
        self.assertEqual(created.status_code, 201)
        pattern_id = created.json()["pattern"]["id"]
        other = self.User.objects.create_user(username="other-user", password="OtherStrongPass123!")
        self.client.force_login(other)
        self.assertEqual(self.client.get("/api/v1/patterns/").json()["patterns"], [])
        patch = self.client.patch(
            f"/api/v1/patterns/{pattern_id}/",
            data=json.dumps({"name": "stolen"}),
            content_type="application/json",
        )
        self.assertEqual(patch.status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/patterns/{pattern_id}/").status_code, 404)

    def test_saved_pattern_workspace_cap(self):
        self.client.force_login(self.user)
        SavedPattern.objects.bulk_create([
            SavedPattern(owner=self.user, name=f"Pattern {index:03}", pattern="a")
            for index in range(100)
        ])
        response = self.post_json("/api/v1/patterns/", {"name": "Pattern 101", "pattern": "b"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("100 saved patterns", response.json()["error"])

    def test_pattern_detail_returns_404_for_missing_item(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.delete("/api/v1/patterns/999999/").status_code, 404)
