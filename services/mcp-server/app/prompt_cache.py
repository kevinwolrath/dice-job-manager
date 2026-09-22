"""A tiny cross-user cache for the /chat tool-*selection* decision (Phase 8).

This only works, and is only safe, because of the exact same invariant the
rest of this project is built on. get_my_jobs() and list_stock() take no
arguments at all — "what are my jobs" always means "call get_my_jobs()", no
matter who's asking, because there is no argument for "who" to go into.
That means the *decision* "this sentence means: call this tool" carries no
user data whatsoever, and is equally true for every caller. Caching it
across users can't leak anything, because the cached value is nothing more
than the name of one tool from the fixed five-tool allow-list — never a
tool result, never an argument, never a token, never anything derived from
one user's data. A cache hit still calls the real tool for real, through
the current caller's own forwarded token, exactly like a cache miss does;
only the decision to call it (which model reasoning would otherwise have to
redo from scratch every time) is served from memory.

This is deliberately why create_job, get_job, and delete_job are left out
of CACHEABLE_TOOLS. Their arguments come from the text of one specific
conversation (a job name someone typed, a job id from earlier in that same
chat) — replaying them for a different caller, or a different moment,
isn't an authorization problem (job-service still resolves ownership from
the token, same as always) but it is very likely the wrong action for that
caller. So they're just not cacheable, on correctness grounds, independent
of the security story.

In-memory only, per dice-mcp-server process — this is a demo proving a
point, not a production cache. It resets on restart and wouldn't be shared
across multiple replicas of dice-mcp-server (this project never runs more
than one), which is a fine trade-off for what this exists to demonstrate:
that a performance optimization doesn't have to, and here structurally
can't, weaken the authorization guarantee the rest of the project is
about.
"""
import re
import threading

# The only tools it is ever safe to serve from a cache shared across every
# user: both take zero arguments, so "which tool to call" is the entire
# decision there is to make — no argument value could ever be stale, wrong,
# or belong to a different conversation.
CACHEABLE_TOOLS = {"get_my_jobs", "list_stock"}

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCTUATION_RE = re.compile(r"[?!.\s]+$")

_lock = threading.Lock()
_cache: dict[str, str] = {}  # normalized prompt -> tool name
_stats = {"hits": 0, "misses": 0}
# Wall-clock time for the WHOLE /chat turn, bucketed by whether it was
# served from cache — this is the actual evidence for "does this make
# things faster," not just "does the count go up." A cache hit skips both
# the tool-selection call to dice-ollama and the reply-phrasing call; a
# miss (when it resolves to a cacheable tool) pays for at least one of
# those, usually two. See app/api/chat.py, which is the only caller.
_timing = {"cached_count": 0, "cached_total_ms": 0.0, "uncached_count": 0, "uncached_total_ms": 0.0}


def normalize(message: str) -> str:
    """Deliberately simple and exact, not semantic/fuzzy. Two different
    phrasings of the same intent ("what are my jobs" vs. "show me my
    jobs") get two different cache entries, each learned independently the
    first time dice-mcp-server sees it. That's a conscious trade-off: a
    fuzzy or embedding-based matcher could misclassify a create/delete
    request as a read (a correctness bug, not a security one — execution
    is still real and still authorized either way) — plain exact-match
    after light normalization can't do that, at the cost of a lower hit
    rate than a smarter matcher would get. Good enough to prove the point;
    a real system would likely want the smarter version.
    """
    text = message.strip().lower()
    text = _TRAILING_PUNCTUATION_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text


def lookup(message: str) -> str | None:
    """Returns the cached tool name for this (normalized) message, or None
    on a cache miss. Safe to call for every message, regardless of which
    user is asking or what conversation history came before it — the
    lookup key is only ever the current message's own text."""
    key = normalize(message)
    with _lock:
        tool_name = _cache.get(key)
        if tool_name is not None:
            _stats["hits"] += 1
        else:
            _stats["misses"] += 1
        return tool_name


def remember(message: str, tool_name: str) -> None:
    """Called only after a real model turn resolved to exactly one tool
    call, to one of the two cacheable tools, with no arguments, and ended
    with a final reply (see app/api/chat.py) — never for a multi-step turn,
    a mutating tool, or a tool call that took arguments."""
    if tool_name not in CACHEABLE_TOOLS:
        return
    key = normalize(message)
    with _lock:
        _cache[key] = tool_name


def record_timing(was_cached: bool, duration_ms: float) -> None:
    """Called once per /chat turn, after the reply is ready, with how long
    the whole turn took (see app/api/chat.py). `was_cached` is the same
    flag the response body reports as "cached" — this is just accumulating
    it into a running average instead of throwing it away."""
    with _lock:
        bucket = "cached" if was_cached else "uncached"
        _timing[f"{bucket}_count"] += 1
        _timing[f"{bucket}_total_ms"] += duration_ms


def stats() -> dict:
    with _lock:
        cached_count = _timing["cached_count"]
        uncached_count = _timing["uncached_count"]
        avg_cached_ms = round(_timing["cached_total_ms"] / cached_count, 1) if cached_count else None
        avg_uncached_ms = (
            round(_timing["uncached_total_ms"] / uncached_count, 1) if uncached_count else None
        )
        return {
            **_stats,
            "learned_patterns": len(_cache),
            "avg_cached_ms": avg_cached_ms,
            "avg_uncached_ms": avg_uncached_ms,
            "timed_requests": {"cached": cached_count, "uncached": uncached_count},
        }
