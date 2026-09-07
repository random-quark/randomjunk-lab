"""{{TITLE}}. Settings and grants arrive through systemd, not a local dotenv."""
import mimetypes
import os
from pathlib import Path
import stat

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

PUBLIC = Path(__file__).parent / 'public'
app = FastAPI(title="{{TITLE}}")

@app.get('/api/health')
def health():
    """Liveness only; this does not assert database/application readiness."""
    return {'ok': True, 'app': os.getenv('APP_NAME', '{{NAME}}')}

def open_public(relative):
    """Open every component without following links, then serve that same fd."""
    parts = relative.split('/') if relative else []
    if any(part in ('.', '..') or '\\' in part or '\x00' in part for part in parts):
        raise HTTPException(status_code=404)
    parts = [part for part in parts if part]
    fd = os.open(PUBLIC, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            next_fd = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            next_fd = os.open('index.html', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            parts.append('index.html')
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise HTTPException(status_code=404)
        stream = os.fdopen(fd, 'rb')
        fd = None
        return stream, info.st_size, mimetypes.guess_type('/'.join(parts))[0] or 'application/octet-stream'
    finally:
        if fd is not None:
            os.close(fd)

@app.get('/{full_path:path}', include_in_schema=False)
def static_or_spa(full_path: str, request: Request):
    # Reject traversal before considering SPA fallback.
    if any(part in ('.', '..') or '\\' in part or '\x00' in part for part in full_path.split('/')):
        raise HTTPException(status_code=404)
    try:
        stream, size, media_type = open_public(full_path)
    except (OSError, HTTPException):
        if ('text/html' not in request.headers.get('accept', '') or
                full_path.startswith('api/') or '.' in full_path.rsplit('/', 1)[-1]):
            raise HTTPException(status_code=404)
        try:
            stream, size, media_type = open_public('index.html')
        except (OSError, HTTPException):
            raise HTTPException(status_code=404)
    def chunks():
        try:
            while chunk := stream.read(65536):
                yield chunk
        finally:
            stream.close()
    return StreamingResponse(chunks(), media_type=media_type,
                             headers={'Content-Length': str(size)},
                             background=BackgroundTask(stream.close))
