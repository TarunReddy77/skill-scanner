import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from skill_scanner.agent import scan_skill

MAX_SKILL_BYTES = 200_000
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="skill-scanner")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/scan")
def scan(
    skill_md: UploadFile = File(...),
    skill_name: str = Form("skill"),
    ignored_files: int = Form(0),
) -> dict:
    """Scan one uploaded SKILL.md. Only SKILL.md is read; other files in the folder are ignored."""
    content = skill_md.file.read(MAX_SKILL_BYTES + 1)
    if len(content) > MAX_SKILL_BYTES:
        raise HTTPException(413, f"SKILL.md is larger than {MAX_SKILL_BYTES // 1000} KB")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "SKILL.md must be a UTF-8 text file")

    # The user-supplied name is only used for the temp folder (sanitized) and trace metadata.
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "-", skill_name)[:64] or "skill"
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / safe_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_bytes(content)
        try:
            verdict = scan_skill(str(skill_dir / "SKILL.md"))
        except Exception as e:
            raise HTTPException(500, f"Scan failed: {type(e).__name__}: {e}")

    return {"skill_name": safe_name, "ignored_files": ignored_files, **verdict.model_dump()}
