import json
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from engine.regex_engine import compile_pattern, ast_json, graph_json, RegexSyntaxError
from playground.models import SavedPattern

class PayloadTooLarge(ValueError):
    """Raised when a JSON API request exceeds the documented body limit."""

def read_payload(request):
    if len(request.body) > 16384:
        raise PayloadTooLarge("Request body exceeds 16 KB")
    data = json.loads(request.body or b"{}")
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data

def dfa_json(dfa):
    return {
        "start": dfa["start"],
        "states": len(dfa["transitions"]),
        "accepts": sorted(dfa["accepts"]),
        "transitions": {str(k): v for k, v in dfa["transitions"].items()},
        "groups": dfa.get("groups", []),
    }

@require_GET
@ensure_csrf_cookie
def home(request):
    return FileResponse(open(settings.BASE_DIR / "index.html", "rb"), content_type="text/html; charset=utf-8")

@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "regex-studio"})

@csrf_exempt
@require_POST
def compile_regex(request):
    try:
        data = read_payload(request)
        pattern = data.get("pattern", "")
        if not isinstance(pattern, str):
            return JsonResponse({"error": "pattern must be a string"}, status=400)
        result = compile_pattern(pattern)
        return JsonResponse({
            "ast": ast_json(result["ast"]),
            "nfa": graph_json(result["nfa"]),
            "dfa": dfa_json(result["dfa"]),
            "minimized_dfa": dfa_json(result["minimized"]),
        })
    except RegexSyntaxError as exc:
        return JsonResponse({"error": exc.message, "position": exc.position}, status=400)
    except PayloadTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)

@csrf_exempt
@require_POST
def simulate_regex(request):
    try:
        data = read_payload(request)
        pattern, text = data.get("pattern", ""), data.get("input", "")
        if not isinstance(pattern, str) or not isinstance(text, str):
            return JsonResponse({"error": "pattern and input must be strings"}, status=400)
        result = compile_pattern(pattern)["nfa"].simulate(text)
        return JsonResponse(result)
    except RegexSyntaxError as exc:
        return JsonResponse({"error": exc.message, "position": exc.position}, status=400)
    except PayloadTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)

# Account and workspace API. These endpoints intentionally use Django session
# authentication and CSRF protection; only the stateless automata endpoints
# above are exempt from CSRF checks.
@require_GET
@ensure_csrf_cookie
def csrf_bootstrap(request):
    return JsonResponse({"csrf": "cookie set"})


def _account_json(user):
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email or "",
        "date_joined": user.date_joined.isoformat() if getattr(user, "date_joined", None) else None,
    }


@require_GET
def account_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False, "user": None})
    return JsonResponse({"authenticated": True, "user": _account_json(request.user)})


@require_POST
def account_register(request):
    try:
        data = read_payload(request)
    except PayloadTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)

    username, email, password = data.get("username", ""), data.get("email", ""), data.get("password", "")
    if not all(isinstance(value, str) for value in (username, email, password)):
        return JsonResponse({"error": "username, email and password must be strings"}, status=400)
    username, email = username.strip(), email.strip()
    User = get_user_model()
    username_field = User._meta.get_field(User.USERNAME_FIELD)
    max_username = username_field.max_length or 150
    if not username or len(username) > max_username:
        return JsonResponse({"error": f"Username must be between 1 and {max_username} characters"}, status=400)
    try:
        username_field.run_validators(username)
    except ValidationError as exc:
        return JsonResponse({"error": "Invalid username: " + "; ".join(exc.messages)}, status=400)
    if len(password) < 8:
        return JsonResponse({"error": "Password must contain at least 8 characters"}, status=400)
    if len(email) > 254:
        return JsonResponse({"error": "Email must be 254 characters or fewer"}, status=400)
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({"error": "Enter a valid email address"}, status=400)
    if User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": username}).exists():
        return JsonResponse({"error": "That username is already in use"}, status=409)

    try:
        with transaction.atomic():
            user = User._default_manager.create_user(**{
                User.USERNAME_FIELD: username,
                "email": email,
                "password": password,
            })
    except IntegrityError:
        return JsonResponse({"error": "That username is already in use"}, status=409)
    login(request, user)
    return JsonResponse({"authenticated": True, "user": _account_json(user)}, status=201)


@require_POST
def account_login(request):
    try:
        data = read_payload(request)
    except PayloadTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)
    username, password = data.get("username", ""), data.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
        return JsonResponse({"error": "Enter both username and password"}, status=400)
    user = authenticate(request, username=username.strip(), password=password)
    if user is None:
        return JsonResponse({"error": "Invalid username or password"}, status=401)
    login(request, user)
    return JsonResponse({"authenticated": True, "user": _account_json(user)})


@require_POST
def account_logout(request):
    logout(request)
    return JsonResponse({"authenticated": False, "user": None})


def _pattern_json(item):
    return {
        "id": item.pk,
        "name": item.name,
        "pattern": item.pattern,
        "flags": item.flags,
        "replacement": item.replacement,
        "test_input": item.test_input,
        "is_favorite": item.is_favorite,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def _validated_pattern_fields(data, existing=None):
    allowed = {"name", "pattern", "flags", "replacement", "test_input", "is_favorite"}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError("Unknown field(s): " + ", ".join(sorted(unknown)))
    current = {
        "name": existing.name if existing else "",
        "pattern": existing.pattern if existing else "",
        "flags": existing.flags if existing else "g",
        "replacement": existing.replacement if existing else "",
        "test_input": existing.test_input if existing else "",
        "is_favorite": existing.is_favorite if existing else False,
    }
    current.update(data)
    for field in ("name", "pattern", "flags", "replacement", "test_input"):
        if not isinstance(current[field], str):
            raise ValueError(f"{field} must be a string")
    current["name"] = current["name"].strip()
    if not current["name"] or len(current["name"]) > 80:
        raise ValueError("Name must be between 1 and 80 characters")
    if len(current["pattern"]) > 512:
        raise ValueError("Pattern must be 512 characters or fewer")
    if len(current["flags"]) > 8 or any(flag not in "dgimsuvy" for flag in current["flags"]):
        raise ValueError("Flags may only contain d, g, i, m, s, u, v and y")
    if len(set(current["flags"])) != len(current["flags"]):
        raise ValueError("Regex flags cannot be duplicated")
    if "u" in current["flags"] and "v" in current["flags"]:
        raise ValueError("Flags u and v cannot be used together")
    if len(current["replacement"]) > 512:
        raise ValueError("Replacement must be 512 characters or fewer")
    if len(current["test_input"]) > 4096:
        raise ValueError("Test input must be 4096 characters or fewer")
    if not isinstance(current["is_favorite"], bool):
        raise ValueError("is_favorite must be a boolean")
    return current


@require_http_methods(["GET", "POST"])
def saved_patterns(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in to access your saved patterns"}, status=401)
    if request.method == "GET":
        items = SavedPattern.objects.filter(owner=request.user)
        query = request.GET.get("q", "").strip()[:80]
        if query:
            items = items.filter(Q(name__icontains=query) | Q(pattern__icontains=query))
        if request.GET.get("favorites") == "1":
            items = items.filter(is_favorite=True)
        return JsonResponse({"patterns": [_pattern_json(item) for item in items[:100]]})

    try:
        data = read_payload(request)
        fields = _validated_pattern_fields(data)
    except PayloadTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)
    if SavedPattern.objects.filter(owner=request.user).count() >= 100:
        return JsonResponse({"error": "Workspace limit reached (100 saved patterns)"}, status=409)
    if SavedPattern.objects.filter(owner=request.user, name__iexact=fields["name"]).exists():
        return JsonResponse({"error": "A saved pattern with that name already exists"}, status=409)
    try:
        with transaction.atomic():
            item = SavedPattern.objects.create(owner=request.user, **fields)
    except IntegrityError:
        return JsonResponse({"error": "A saved pattern with that name already exists"}, status=409)
    return JsonResponse({"pattern": _pattern_json(item)}, status=201)


@require_http_methods(["PATCH", "DELETE"])
def saved_pattern_detail(request, pattern_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in to manage saved patterns"}, status=401)
    try:
        item = SavedPattern.objects.get(pk=pattern_id, owner=request.user)
    except SavedPattern.DoesNotExist:
        return JsonResponse({"error": "Saved pattern not found"}, status=404)

    if request.method == "DELETE":
        item.delete()
        return JsonResponse({"deleted": True, "id": pattern_id})

    try:
        data = read_payload(request)
        fields = _validated_pattern_fields(data, existing=item)
    except PayloadTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)
    if SavedPattern.objects.filter(owner=request.user, name__iexact=fields["name"]).exclude(pk=item.pk).exists():
        return JsonResponse({"error": "A saved pattern with that name already exists"}, status=409)
    for field, value in fields.items():
        setattr(item, field, value)
    try:
        with transaction.atomic():
            item.save()
    except IntegrityError:
        return JsonResponse({"error": "A saved pattern with that name already exists"}, status=409)
    return JsonResponse({"pattern": _pattern_json(item)})
