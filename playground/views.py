import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from engine.regex_engine import compile_pattern, ast_json, graph_json, RegexSyntaxError

@require_GET
def health(request):
    return JsonResponse({'status':'ok','service':'regex-studio'})

@require_POST
def compile_regex(request):
    if len(request.body)>16384: return JsonResponse({'error':'Request body exceeds 16 KB'},status=413)
    try:
        data=json.loads(request.body or b'{}')
        pattern=data.get('pattern','')
        if not isinstance(pattern,str): return JsonResponse({'error':'pattern must be a string'},status=400)
        result=compile_pattern(pattern)
        nfa=result['nfa']; dfa=result['dfa']; mini=result['minimized']
        return JsonResponse({'ast':ast_json(result['ast']),'nfa':graph_json(nfa),'dfa':{'states':len(dfa['transitions']),'accepts':sorted(dfa['accepts'])},'minimized_dfa':{'states':len(mini['transitions']),'accepts':sorted(mini['accepts']),'groups':mini['groups']}})
    except RegexSyntaxError as exc:
        return JsonResponse({'error':exc.message,'position':exc.position},status=400)
    except (ValueError,TypeError,json.JSONDecodeError) as exc:
        return JsonResponse({'error':str(exc) or 'Invalid request'},status=400)
