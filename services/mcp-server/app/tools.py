"""The tool implementations dice-mcp-server exposes to a model, through both
the real MCP protocol surface (app/mcp_tools.py, at /mcp) and the /chat
demo endpoint (app/api/chat.py).

Every function here takes `token` — the calling human's own already-verified
JWT, forwarded unchanged to job-service/stock-service exactly as it arrived —
and otherwise takes ONLY the parameters an end user would supply when asking
for the thing in plain language (a job's own fields, a job_id it already
owns). None of them takes a user_id, and none ever could without changing
the function signature a reviewer can see at a glance: authorization is
enforced by job-service and stock-service themselves (they resolve "mine"
from this same token), never by anything decided here or by whatever the
model chooses to pass in. This holds regardless of what a user types,
including a prompt-injection attempt embedded in job descriptions or other
data the model reads back — there is no parameter here for such an attempt
to land in that would change whose data gets touched.
"""
import httpx

from app.core.config import get_settings

settings = get_settings()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def get_my_jobs(token: str) -> list[dict]:
    """List every dice job belonging to the calling user. Takes no
    parameters — "my jobs" always means the jobs owned by whoever this
    request's token belongs to, never anyone the model names."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{settings.job_service_url}/dice-jobs", headers=_auth_headers(token))
        resp.raise_for_status()
        return resp.json()


async def get_job(token: str, job_id: str) -> dict:
    """Get one dice job by its id. Only works if the calling user owns it —
    job-service returns "not found" (not a permission error) for a job_id
    that exists but belongs to someone else, so this can't be used to probe
    whether an id belongs to another user."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{settings.job_service_url}/dice-jobs/{job_id}", headers=_auth_headers(token))
        resp.raise_for_status()
        return resp.json()


async def create_job(
    token: str,
    job_name: str,
    colour_count: int,
    material_type_id: str,
    production_method_id: str,
    dice_job_number_colour_id: str,
    description: str | None = None,
) -> dict:
    """Create a new dice job. It is always created as owned by the calling
    user — there is no field to set a different owner. material_type_id,
    production_method_id, and dice_job_number_colour_id are stock-service
    reference-data ids; call list_stock() first to find valid ones."""
    payload = {
        "job_name": job_name,
        "colour_count": colour_count,
        "material_type_id": material_type_id,
        "production_method_id": production_method_id,
        "dice_job_number_colour_id": dice_job_number_colour_id,
        "description": description,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{settings.job_service_url}/dice-jobs", json=payload, headers=_auth_headers(token)
        )
        resp.raise_for_status()
        return resp.json()


async def delete_job(token: str, job_id: str) -> dict:
    """Delete a dice job by id. Only works if the calling user owns it, for
    the same reason as get_job."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.delete(
            f"{settings.job_service_url}/dice-jobs/{job_id}", headers=_auth_headers(token)
        )
        resp.raise_for_status()
    return {"deleted": True, "job_id": job_id}


async def list_stock(token: str) -> dict:
    """List the shared reference data every user needs to create a dice
    job: material types, production methods, and dice job number colours.
    Available to every authenticated user regardless of role — the admin
    role only gates writing this data in dice-stock-service, never reading
    it, so this tool needs no special permission to call."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        material_types_resp = await client.get(
            f"{settings.stock_service_url}/material-types", headers=_auth_headers(token)
        )
        production_methods_resp = await client.get(
            f"{settings.stock_service_url}/production-methods", headers=_auth_headers(token)
        )
        colours_resp = await client.get(
            f"{settings.stock_service_url}/dice-job-number-colours", headers=_auth_headers(token)
        )
    material_types_resp.raise_for_status()
    production_methods_resp.raise_for_status()
    colours_resp.raise_for_status()
    return {
        "material_types": material_types_resp.json(),
        "production_methods": production_methods_resp.json(),
        "dice_job_number_colours": colours_resp.json(),
    }
