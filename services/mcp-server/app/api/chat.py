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
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app import prompt_cache
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


def _render_my_jobs_reply(result) -> str:
    if isinstance(result, dict) and "error" in result:
        return f"I couldn't look up your dice jobs just now ({result['error']})."
    jobs = result or []
    # This template gets reused verbatim for whatever normalized text
    # first taught the cache "this means get_my_jobs()" — which can be a
    # phrasing that named someone else ("show me Jane's jobs" resolves to
    # this same safe, zero-arg call, since that's the only jobs-listing
    # tool that exists). Without this line, a cache hit on a message like
    # that reads as a non-sequitur: it never acknowledges what was asked,
    # just lists a different user's jobs than the one named. This line is
    # the fix — always state the guarantee, so the reply makes sense
    # regardless of how the question was worded, instead of silently
    # answering a blander question than the one actually asked.
    prefix = "(This always shows only your own jobs, no matter how the question is worded.) "
    if not jobs:
        return prefix + "You don't have any dice jobs yet."
    plural = "s" if len(jobs) != 1 else ""
    lines = [prefix + f"You have {len(jobs)} dice job{plural}:"]
    lines += [f"- {job.get('job_name', '(unnamed job)')}" for job in jobs]
    return "\n".join(lines)


def _render_stock_reply(result) -> str:
    if isinstance(result, dict) and "error" in result:
        return f"I couldn't look up the shared reference data just now ({result['error']})."
    material_types = result.get("material_types") or []
    production_methods = result.get("production_methods") or []
    colours = result.get("dice_job_number_colours") or []
    return "\n".join(
        [
            "Here's the shared reference data available for creating a dice job:",
            "- Material types: " + (", ".join(m["description"] for m in material_types) or "none yet"),
            "- Production methods: "
            + (", ".join(m["description"] for m in production_methods) or "none yet"),
            "- Dice job number colours: "
            + (", ".join(c["dice_job_number_colour_name"] for c in colours) or "none yet"),
        ]
    )


# One hand-written template per cacheable tool (app/prompt_cache.py) — used
# only on a cache hit, where there's no model turn left to phrase a reply,
# just a real, freshly-fetched, correctly-scoped result to describe in
# plain language. Deliberately plain and mechanical rather than clever:
# the point of a cache hit is skipping the model entirely, not imitating it.
_CACHED_REPLY_RENDERERS = {
    "get_my_jobs": _render_my_jobs_reply,
    "list_stock": _render_stock_reply,
}


@router.get("/cache-stats")
def cache_stats(_token: str = Depends(current_user_token)):
    """Hit/miss counts, how many prompt->tool patterns have been learned so
    far, and average turn duration for cached vs. uncached turns (see
    app/prompt_cache.py) — the actual evidence for whether the cache is
    worth having, not just whether it's firing. No prompt text, no user
    data, and no per-user breakdown lives here — it's aggregate counts and
    averages only, which is also why this is safe to serve to any
    authenticated user rather than needing its own authorization story."""
    return prompt_cache.stats()


@router.post("/chat")
async def chat(payload: dict, token: str = Depends(current_user_token)):
    """payload: {"message": str, "history": [{"role": "user"|"assistant", "content": str}, ...]}

    Returns {"reply": str, "toolCalls": [...], "cached": bool, "tookMs": float}
    — toolCalls is the full trace of what actually ran this turn (each
    entry also says whether IT was cached), so the UI can show it: the
    point of this demo is watching that trace stay confined to the
    logged-in user's own data no matter how the chat message is worded, or
    whether it came from the model or from the cache. tookMs is wall-clock
    time for this whole turn, measured server-side (from the moment this
    handler started to the moment it's about to respond) so it's directly
    comparable across turns regardless of client-side network variance —
    that's the actual evidence for "caching makes this faster," not just
    the hit/miss counters on their own.

    Cache-hit path (Phase 8, see app/prompt_cache.py): if this exact
    message has previously resolved to one of the two zero-argument,
    read-only tools, skip Ollama entirely — both the "which tool" reasoning
    and the "how do I phrase this" reasoning — and go straight to calling
    that tool for real, through THIS caller's own forwarded token, then
    describe the result with a plain template. Nothing about who is asking
    changes which tool gets called or what data comes back; only whether a
    model had to be asked which tool to use.
    """
    start = time.perf_counter()

    def _took_ms() -> float:
        return round((time.perf_counter() - start) * 1000, 1)

    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    history = payload.get("history") or []

    cached_tool_name = prompt_cache.lookup(message)
    if cached_tool_name is not None:
        result = await _call_tool(cached_tool_name, {}, token)
        reply = _scrub_internal_names(_CACHED_REPLY_RENDERERS[cached_tool_name](result))
        took_ms = _took_ms()
        prompt_cache.record_timing(was_cached=True, duration_ms=took_ms)
        return {
            "reply": reply,
            "toolCalls": [{"name": cached_tool_name, "arguments": {}, "result": result, "cached": True}],
            "cached": True,
            "tookMs": took_ms,
        }

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
                # Learn from this turn (Phase 8) only when it was the
                # simplest possible shape: exactly one tool call, to one of
                # the two cacheable tools, with no arguments, immediately
                # followed by a final answer. A multi-step turn (e.g.
                # list_stock() then create_job(...)) never qualifies —
                # list_stock() there is a means to an end, not "the whole
                # answer to what was asked", and remembering it in that
                # context would (harmlessly, but wrongly) serve a
                # create-job request's setup step as if it were a
                # standalone "show me the stock" question.
                if (
                    len(tool_call_trace) == 1
                    and tool_call_trace[0]["name"] in prompt_cache.CACHEABLE_TOOLS
                    and not tool_call_trace[0]["arguments"]
                ):
                    prompt_cache.remember(message, tool_call_trace[0]["name"])
                took_ms = _took_ms()
                prompt_cache.record_timing(was_cached=False, duration_ms=took_ms)
                return {"reply": reply, "toolCalls": tool_call_trace, "cached": False, "tookMs": took_ms}

            messages.append(assistant_message)
            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name")
                arguments = _parse_tool_arguments(function.get("arguments"))
                result = await _call_tool(name, arguments, token)
                tool_call_trace.append({"name": name, "arguments": arguments, "result": result, "cached": False})
                messages.append({"role": "tool", "content": json.dumps(result)})

        took_ms = _took_ms()
        prompt_cache.record_timing(was_cached=False, duration_ms=took_ms)
        return {
            "reply": "Stopped after several tool calls without a final answer — try rephrasing.",
            "toolCalls": tool_call_trace,
            "cached": False,
            "tookMs": took_ms,
        }
