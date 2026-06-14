import ast
import json
import math
import operator
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["SESSIONS_TABLE"]
SECRET_ARN = os.environ["LLM_SECRET_ARN"]
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_URL = os.environ.get("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
MAX_ITERS = int(os.environ.get("AGENT_MAX_ITERS", "5"))
HISTORY_LIMIT = int(os.environ.get("AGENT_HISTORY_LIMIT", "20"))

CHUNKS_TABLE = os.environ.get("CHUNKS_TABLE")
EMB_SECRET_ARN = os.environ.get("EMBEDDINGS_SECRET_ARN")
EMB_URL = os.environ.get("EMBEDDINGS_API_URL", "https://api.jina.ai/v1/embeddings")
EMB_MODEL = os.environ.get("EMBEDDINGS_MODEL", "jina-embeddings-v3")
SEARCH_TOP_K = int(os.environ.get("SEARCH_TOP_K", "3"))

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools and memory of the "
    "conversation so far. Use search_corpus whenever the user asks about "
    "internal, company, or document-specific facts, and base your answer on "
    "the passages it returns. Use the other tools for the current time or "
    "exact arithmetic. After using tools, give a clear, concise final answer."
)

table = boto3.resource("dynamodb").Table(TABLE_NAME)
chunks_table = boto3.resource("dynamodb").Table(CHUNKS_TABLE) if CHUNKS_TABLE else None
_secrets = boto3.client("secretsmanager")
_api_key = None
_emb_key = None

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in UTC.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a basic arithmetic expression and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "An arithmetic expression, e.g. '23 * 19 + 4'.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_corpus",
            "description": (
                "Search the internal document corpus for passages relevant to a "
                "question. Use this for company, internal, or document-specific "
                "facts you would otherwise not know."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expr):
    def _ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
            return _SAFE_OPS[type(node.op)](_ev(node.left), _ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
            return _SAFE_OPS[type(node.op)](_ev(node.operand))
        raise ValueError("Unsupported expression")

    return _ev(ast.parse(expr, mode="eval").body)


def _get_api_key():
    global _api_key
    if _api_key is None:
        _api_key = _secrets.get_secret_value(SecretId=SECRET_ARN)["SecretString"].strip()
    return _api_key


def _get_emb_key():
    global _emb_key
    if _emb_key is None:
        _emb_key = _secrets.get_secret_value(SecretId=EMB_SECRET_ARN)["SecretString"].strip()
    return _emb_key


def _embed_query(text):
    payload = json.dumps(
        {"model": EMB_MODEL, "task": "retrieval.query", "normalized": True, "input": [text]}
    ).encode("utf-8")
    req = urllib.request.Request(
        EMB_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {_get_emb_key()}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; agent-platform/1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["data"][0]["embedding"]


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _scan_chunks():
    items = []
    kwargs = {
        "ProjectionExpression": "doc_id, chunk_id, #t, embedding",
        "ExpressionAttributeNames": {"#t": "text"},
    }
    while True:
        resp = chunks_table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _tool_search_corpus(args):
    query = str(args.get("query", "")).strip()
    if not query:
        return "Empty query."
    if chunks_table is None:
        return "No corpus is configured."
    qvec = _embed_query(query)
    scored = []
    for it in _scan_chunks():
        try:
            vec = json.loads(it["embedding"])
        except (KeyError, json.JSONDecodeError):
            continue
        scored.append((_cosine(qvec, vec), it.get("text", ""), it.get("doc_id", "")))
    if not scored:
        return "The corpus is empty; no passages to search."
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:SEARCH_TOP_K]
    return "\n\n".join(
        f"[source: {src} | score {score:.3f}]\n{text}" for score, text, src in top
    )


def _tool_get_current_time(_args):
    return datetime.now(timezone.utc).isoformat()


def _tool_calculate(args):
    try:
        return str(_safe_eval(str(args.get("expression", ""))))
    except Exception:
        return "Error: invalid arithmetic expression."


TOOL_IMPLS = {
    "get_current_time": _tool_get_current_time,
    "calculate": _tool_calculate,
    "search_corpus": _tool_search_corpus,
}


def _load_history(session_id):
    resp = table.query(
        KeyConditionExpression=Key("session_id").eq(session_id),
        ScanIndexForward=False,
        Limit=HISTORY_LIMIT,
        ConsistentRead=True,
    )
    items = list(reversed(resp.get("Items", [])))
    history = []
    for it in items:
        role, content = it.get("role"), it.get("message", "")
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    return history


def _call_model(messages):
    payload = json.dumps(
        {"model": LLM_MODEL, "messages": messages, "tools": TOOLS, "tool_choice": "auto"}
    ).encode("utf-8")
    req = urllib.request.Request(
        LLM_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; agent-platform/1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]


def _run_agent(history, user_message):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    trace = []
    for _ in range(MAX_ITERS):
        msg = _call_model(messages)
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return msg.get("content") or "", trace
        messages.append(msg)
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = TOOL_IMPLS.get(name)
            result = impl(args) if impl else f"Unknown tool: {name}"
            trace.append({"tool": name, "args": args, "result": str(result)[:500]})
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": str(result)}
            )
    return "I couldn't finish within the allowed number of steps.", trace


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _resp(400, {"error": "Invalid JSON body"})

    message = body.get("message")
    if not message:
        return _resp(400, {"error": "Field 'message' is required"})

    session_id = body.get("session_id") or str(uuid.uuid4())
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user = claims.get("email") or claims.get("sub") or "unknown"

    history = _load_history(session_id)
    _save_turn(session_id, "user", message, user)

    try:
        reply, trace = _run_agent(history, message)
    except urllib.error.HTTPError as e:
        return _resp(502, {"error": "Model call failed", "detail": e.read().decode("utf-8", "ignore")[:400]})
    except Exception as e:
        return _resp(502, {"error": "Agent failed", "detail": str(e)})

    _save_turn(session_id, "assistant", reply, user)

    return _resp(200, {"session_id": session_id, "reply": reply, "tool_calls": trace})


def _save_turn(session_id, role, content, user):
    table.put_item(
        Item={
            "session_id": session_id,
            "turn_id": f"{int(time.time() * 1000)}#{uuid.uuid4().hex[:8]}",
            "role": role,
            "message": content,
            "user": user,
            "created_at": int(time.time()),
        }
    )


def _resp(status, payload):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(payload),
    }
