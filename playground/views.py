import json
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from engine.regex_engine import compile_pattern, ast_json, graph_json, RegexSyntaxError

def read_payload(request):
    if len(request.body) > 16384:
        raise ValueError("Request body exceeds 16 KB")
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
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Invalid request"}, status=400)
