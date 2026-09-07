"""{{TITLE}} — FastAPI app scaffolded by newlab.

Routing note: static files are NOT mounted at "/". A StaticFiles mount at the
root captures every request before later routes, which makes an SPA fallback
unreachable and turns a missing asset into an index.html response. Instead the
catch-all below serves real files itself and only falls back to index.html for
navigation requests, so a missing .js still returns a proper 404.

After editing:  sudo /usr/local/sbin/labctl service restart {{NAME}}
Logs:           sudo /usr/local/sbin/labctl logs {{NAME}}
"""
import os
import pathlib

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

# /etc/lab/apps/<name>.env is supplied by systemd and holds only the secrets
# this app was explicitly granted. .env holds non-secret settings.
load_dotenv(".env", override=False)

APP_NAME = os.getenv("APP_NAME", "{{NAME}}")
DATABASE_URL = os.getenv("DATABASE_URL")

PUBLIC = pathlib.Path(__file__).parent / "public"

app = FastAPI(title="{{TITLE}}")


@app.get("/api/health")
def health():
    """Liveness check. newlab waits on this, so keep it dependency-free."""
    return {"ok": True, "app": APP_NAME, "db": bool(DATABASE_URL)}


@app.get("/{full_path:path}", include_in_schema=False)
def static_or_spa(full_path: str, request: Request):
    root = PUBLIC.resolve()
    candidate = (PUBLIC / full_path).resolve()

    # A directory means its index.html — "/" and "/docs/" both work.
    if candidate.is_dir():
        candidate = candidate / "index.html"

    # Serve the real file when it exists and is genuinely inside public/.
    # is_relative_to on the resolved path is what blocks ../ traversal.
    if candidate.is_file() and candidate.is_relative_to(root):
        return FileResponse(candidate)

    # Only navigations fall back to the shell; a missing asset is a 404.
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse(PUBLIC / "index.html")

    raise HTTPException(status_code=404)
