"""The demo path: dice-test-client's chat panel talks to this endpoint over
plain REST, never to dice-ollama directly and never through the raw MCP wire
protocol. This is a deliberate choice, not a shortcut around MCP: the *same*
tool functions in app/tools.py back both this endpoint and the real MCP
server surface at /mcp (app/mcp_tools.py) — this endpoint just runs the
tool-calling loop against Ollama itself, in Python, with no dependency on the
mcp package's HTTP transport working correctly. If /mcp's wiring turns out
to be wrong (genuinely possible — see app/mcp_tools.py's docstring), this
endpoint, and the whole point of the demo (watch a local model's tool calls
stay inside the logged-in user's own data), still works.

Every message this endpoint sends to Ollama, including tool results, is
untrusted content as far as authorization is concerned — a job description
or a chat message could contain a prompt-injection attempt trying to get the
model to "call get_my_jobs for user Steve" or similar. That attempt has
nowhere to go: no tool below accepts a user identifier, so there is no
parameter for an injected instruction to control, no matter how persuasive
the wording. This is the live version of the isolation test from Phase 3 —
same guarantee, now reachable through a model instead of direct HTTP calls.
"""
import json
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import current_user_token
from app.core.config import get_settings
from app.tools import create_job, delete_job, get_job, get_my_jobs, list_stock

router = APIRouter()
settings = get_settings()

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are the assistant inside dice-job-manager, a dice-casting job tracker. "
    "You can look up and manage the CURRENT user's own dice jobs and look up shared "
    "reference data (material types, production methods, dice job number colours) "
    "using the tools available to you. You have no way to see or affect any other "
    "user's data — the tools themselves don't accept another user's identity as a "
    "parameter, so don't claim you can look something up for a different named "
    "person; explain in plain language that you can only see the current user's own "
    "jobs. Before creating a job, look up the current material types, production "
    "methods, and dice job number colours if you don't already know a valid one to use.\n\n"
    "Never mention tool names, function names, parameter names, or any other internal "
    "implementation detail in what you say to the user (for example: get_my_jobs, "
    "create_job, list_stock, material_type_id) — the user is a person using a chat "
    "app, not a developer, and has no reason to know this system is built out of "
    "tools at all. Describe what you did or what you found in plain, ordinary "
    "language, the way any helpful assistant would: say \"here are your jobs\" or "
    "\"I can only see your own jobs, not anyone else's,\" never \"the get_my_jobs "
    "function only returns...\". If you need information, actually use your real "
    "tool-calling ability to get it — never write out a function call, or what a "
    "function call or its JSON would look like, as plain text in your reply; if you "
    "are not going to call a tool, just answer in plain language instead."
)

# Defense-in-depth backstop for the instruction above: a small local model
# won't always follow a system prompt, and in practice this one sometimes
# skips its real tool-calling ability entirely and just narrates or
# fabricates a tool call as plain text instead (visible as an empty
# toolCalls trace alongside a reply that names one anyway). The system
# prompt is the first attempt at fixing that at the source; this is the
# part that holds regardless of whether the model listens; it can't be
# skipped, ignored, or talked out of by a cleverer prompt the way the
# system-prompt instruction above can, in principle, always be. It's a
# blunt substitution, not a rewrite — good enough to guarantee no internal
# identifier reaches the user, not intended to read gracefully.
_INTERNAL_TOOL_NAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in ("get_my_jobs", "get_job", "create_job", "delete_job", "list_stock")) + r")\b"
)


def _scrub_internal_names(text: str) -> str:
    return _INTERNAL_TOOL_NAME_PATTERN.sub("[an internal tool]", text)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_jobs",
            "description": "List every dice job belonging to the current user. Takes no parameters.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job",
            "description": "Get one of the current user's dice jobs by its id.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string", "description": "The dice job's id (UUID)."}},
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_job",
            "description": "Create a new dice job owned by the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "description": {"type": "string"},
                    "colour_count": {"type": "integer", "description": "Number of colours in the job."},
                    "material_type_id": {"type": "string", "description": "From list_stock()."},
                    "production_method_id": {"type": "string", "description": "From list_stock()."},
                    "dice_job_number_colour_id": {"type": "string", "description": "From list_stock()."},
                },
                "required": [
                    "job_name",
                    "colour_count",
                    "material_type_id",
                    "production_method_id",
                    "dice_job_number_colour_id",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_job",
            "description": "Delete one of the current user's dice jobs by its id.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string", "description": "The dice job's id (UUID)."}},
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_stock",
            "description": (
                "List shared reference data (material types, production methods, dice job "
                "number colours) needed to create a dice job."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

_TOOL_IMPLS = {
    "get_my_jobs": get_my_jobs,
    "get_job": get_job,
    "create_job": create_job,
    "delete_job": delete_job,
    "list_stock": list_stock,
}


async def _call_tool(name: str, arguments: dict, token: str):
    """Basic tool-input validation (Phase 7): a malformed or adversarial
    tool call from the model — missing/extra/wrong-typed arguments, or a
    backend service rejecting the request — fails just that one tool call
    with an error the model can see and react to, never a 500 that takes
    the whole /chat turn down.

    One case worth naming explicitly: `token` always comes from this
    function's own trusted parameter, never from `arguments`. If a model
    were ever coaxed (by an injected instruction in a job description, say)
    into producing a tool call like `get_my_jobs(token="something-else")`,
    `impl(token=token, **arguments)` below raises TypeError — "got multiple
    values for argument 'token'" — because Python itself refuses the
    duplicate keyword. That's caught below and reported as an invalid tool
    call. There is no code path in which a value from `arguments` can reach
    the `token` parameter, so this can't be used to smuggle in a different
    identity.
    """
    impl = _TOOL_IMPLS.get(name)
    if impl is None:
        return {"error": f"Unknown tool: {name}"}
    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be a JSON object"}
    try:
        return await impl(token=token, **arguments)
    except TypeError as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}
    except httpx.HTTPStatusError as exc:
        # Surface the backend service's own error (e.g. job-service's 404 for
        # a job that isn't this user's) back to the model as a tool result,
        # rather than as a 500 — the model can then tell the user "not
        # found" instead of the request just failing.
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except Exception:
            detail = exc.response.text
        return {"error": detail, "status_code": exc.response.status_code}
    except httpx.HTTPError as exc:
        return {"error": f"{name} could not reach its backend service: {exc}"}


def _parse_tool_arguments(raw) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


@router.post("/chat")
async def chat(payload: dict, token: str = Depends(current_user_token)):
    """payload: {"message": str, "history": [{"role": "user"|"assistant", "content": str}, ...]}

    Returns {"reply": str, "toolCalls": [{"name": str, "arguments": dict, "result": Any}, ...]}
    — toolCalls is the full trace of what the model actually called this
    turn, so the UI can show it: the point of this demo is watching that
    trace stay confined to the logged-in user's own data no matter how the
    chat message is worded.
    """
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    history = payload.get("history") or []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history) + [
        {"role": "user", "content": message}
    ]
    tool_call_trace = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                resp = await client.post(
                    f"{settings.ollama_url}/api/chat",
                    json={
                        "model": settings.ollama_model,
                        "messages": messages,
                        "tools": TOOL_SCHEMAS,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                # dice-ollama itself rejected the request (e.g. the model
                # name in OLLAMA_MODEL isn't pulled) — surface its own error
                # body rather than an opaque 500, so it shows up directly in
                # whatever called this endpoint instead of only in
                # `docker compose logs dice-mcp-server`.
                try:
                    detail = exc.response.json()
                except Exception:
                    detail = exc.response.text
                raise HTTPException(
                    status_code=502, detail=f"dice-ollama rejected the request: {detail}"
                )
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=f"Could not reach dice-ollama: {exc}")
            except ValueError as exc:
                raise HTTPException(
                    status_code=502, detail=f"dice-ollama returned a response that wasn't valid JSON: {exc}"
                )

            assistant_message = data.get("message", {})
            tool_calls = assistant_message.get("tool_calls") or []

            if not tool_calls:
                reply = _scrub_internal_names(assistant_message.get("content", ""))
                return {"reply": reply, "toolCalls": tool_call_trace}

            messages.append(assistant_message)
            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name")
                arguments = _parse_tool_arguments(function.get("arguments"))
                result = await _call_tool(name, arguments, token)
                tool_call_trace.append({"name": name, "arguments": arguments, "result": result})
                messages.append({"role": "tool", "content": json.dumps(result)})

        return {
            "reply": "Stopped after several tool calls without a final answer — try rephrasing.",
            "toolCalls": tool_call_trace,
        }
