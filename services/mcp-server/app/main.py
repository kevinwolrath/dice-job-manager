import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health
from app.core.config import get_settings

logger = logging.getLogger("dice-mcp-server")

# Imported defensively: app/mcp_tools.py depends on the `mcp` package's
# FastMCP/streamable-http API, which is the one piece of this phase built
# without being able to run it first (see that file's docstring). If it
# fails to import or mount, /mcp just isn't available — /chat, the endpoint
# dice-test-client's chat panel actually calls, only depends on app/tools.py
# and doesn't go anywhere near this.
mcp_server = None
_mcp_auth_middleware_cls = None
try:
    from app.mcp_tools import AuthMiddleware as _mcp_auth_middleware_cls
    from app.mcp_tools import mcp_server
except Exception as exc:  # noqa: BLE001 - intentionally broad, see docstring above
    logger.warning("dice-mcp-server: /mcp unavailable at import time: %s", exc)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if mcp_server is not None:
        try:
            async with mcp_server.session_manager.run():
                yield
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning("dice-mcp-server: /mcp session manager failed to start: %s", exc)
    yield


app = FastAPI(title="dice-mcp-server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)

if mcp_server is not None and _mcp_auth_middleware_cls is not None:
    try:
        app.mount("/mcp", _mcp_auth_middleware_cls(mcp_server.streamable_http_app()))
    except Exception as exc:  # noqa: BLE001
        logger.warning("dice-mcp-server: could not mount /mcp: %s", exc)
