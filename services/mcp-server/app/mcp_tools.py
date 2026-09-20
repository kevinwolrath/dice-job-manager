"""The genuine MCP protocol surface — mounted at /mcp by app/main.py so a
real MCP client (Claude Desktop, the `mcp` CLI inspector, another agent
host) can connect to this service directly over streamable HTTP, not just
dice-test-client's bespoke /chat endpoint.

This is the one file in this phase built against an SDK (the official
`mcp` Python package's FastMCP + streamable-http transport) I could not
actually run anywhere before shipping it — my sandbox has no network access
to install it, so this is written from documented/remembered API shape, not
verified. If it's wrong, app/main.py is written to catch that at startup and
disable /mcp without taking the rest of the service down (the /chat endpoint
that dice-test-client actually uses doesn't import anything from this file's
runtime behavior — only app/tools.py, which is plain httpx code already
proven out in earlier phases). Tell me the traceback if `docker compose logs
dice-mcp-server` shows this failing to import or mount and I'll fix it.

Auth model: FastMCP's streamable-http transport handles one HTTP request at
a time even across a session, so a Starlette-level ASGI middleware
(AuthMiddleware, below) that reads the Authorization header and stashes the
verified bearer token in a contextvar BEFORE calling into the mounted app is
enough for every tool call in that request to see the right token — no need
to touch FastMCP's own request/context API, which is the part most likely to
have moved between SDK versions.
"""
import contextvars

import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import decode_access_token
from app.tools import create_job, delete_job, get_job, get_my_jobs, list_stock

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - surfaced to app/main.py's import guard
    raise

_current_token: contextvars.ContextVar[str] = contextvars.ContextVar("dice_mcp_current_token")

mcp_server = FastMCP("dice-mcp-server", stateless_http=True)


def _token() -> str:
    return _current_token.get()


@mcp_server.tool()
async def get_my_jobs_tool() -> list[dict]:
    """List every dice job belonging to the current user. Takes no parameters."""
    return await get_my_jobs(token=_token())


@mcp_server.tool()
async def get_job_tool(job_id: str) -> dict:
    """Get one of the current user's dice jobs by its id."""
    return await get_job(token=_token(), job_id=job_id)


@mcp_server.tool()
async def create_job_tool(
    job_name: str,
    colour_count: int,
    material_type_id: str,
    production_method_id: str,
    dice_job_number_colour_id: str,
    description: str | None = None,
) -> dict:
    """Create a new dice job owned by the current user."""
    return await create_job(
        token=_token(),
        job_name=job_name,
        colour_count=colour_count,
        material_type_id=material_type_id,
        production_method_id=production_method_id,
        dice_job_number_colour_id=dice_job_number_colour_id,
        description=description,
    )


@mcp_server.tool()
async def delete_job_tool(job_id: str) -> dict:
    """Delete one of the current user's dice jobs by its id."""
    return await delete_job(token=_token(), job_id=job_id)


@mcp_server.tool()
async def list_stock_tool() -> dict:
    """List shared reference data (material types, production methods, dice job
    number colours) needed to create a dice job."""
    return await list_stock(token=_token())


class AuthMiddleware:
    """Pure ASGI middleware (not Starlette's BaseHTTPMiddleware, which can
    run the downstream app in a spawned task) so the contextvar set here is
    guaranteed visible to every tool call handled within this same request —
    contextvars propagate to child tasks spawned *after* the value is set,
    but not the other way around.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            response = JSONResponse({"detail": "Missing bearer token"}, status_code=401)
            await response(scope, receive, send)
            return

        token = auth.split(" ", 1)[1]
        try:
            decode_access_token(token)
        except jwt.PyJWTError:
            response = JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
            await response(scope, receive, send)
            return

        reset_token = _current_token.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_token.reset(reset_token)
