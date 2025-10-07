from __future__ import annotations

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os
import subprocess
import threading

from config.settings import settings
from src.database.models import init_database, AIDecisionLog
from sqlalchemy.orm import Session


def basic_auth_dependency(request: Request):
    user = os.getenv("ADMIN_BASIC_AUTH_USER")
    pwd = os.getenv("ADMIN_BASIC_AUTH_PASS")
    if not user and not pwd:
        return
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("basic "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    import base64
    try:
        dec = base64.b64decode(auth.split(" ",1)[1]).decode()
        u, p = dec.split(":",1)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    if u != user or p != pwd:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})


def create_app() -> FastAPI:
    app = FastAPI(title="AI Support Admin", root_path=os.getenv("ADMIN_ROOT_PATH", ""))

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    os.makedirs(templates_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
    templates = Jinja2Templates(directory=templates_dir)

    SessionMaker = init_database()

    def get_db():
        db = SessionMaker()
        try:
            yield db
        finally:
            db.close()

    @app.get("/", response_class=HTMLResponse)
    def index():
        return RedirectResponse(url="/reviews")

    @app.get("/reviews", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def reviews(request: Request, db: Session = Depends(get_db), limit: int = 50):
        rows = db.query(AIDecisionLog).order_by(AIDecisionLog.id.desc()).limit(limit).all()
        return templates.TemplateResponse("reviews.html", {"request": request, "rows": rows})

    @app.post("/feedback", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def feedback(request: Request, id: int = Form(...), feedback: str = Form("approved"), notes: str = Form(""), db: Session = Depends(get_db)):
        row = db.query(AIDecisionLog).filter(AIDecisionLog.id==id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Row not found")
        row.human_feedback = feedback
        row.human_notes = notes
        db.commit()
        return RedirectResponse(url="/reviews", status_code=303)

    @app.get("/rules", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def rules_get(request: Request):
        rules_path = os.path.join("config", "policies", "rules.md")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        return templates.TemplateResponse("rules.html", {"request": request, "content": content})

    @app.post("/rules", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def rules_post(request: Request, content: str = Form("")):
        rules_dir = os.path.join("config", "policies")
        os.makedirs(rules_dir, exist_ok=True)
        with open(os.path.join(rules_dir, "rules.md"), "w", encoding="utf-8") as f:
            f.write(content)
        return RedirectResponse(url="/rules", status_code=303)

    # Preparation UI
    @app.get("/prep", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def prep_get(request: Request):
        return templates.TemplateResponse("prep.html", {"request": request})

    def _run_prep(ids_text: str, limit: int, model: str, no_ai: bool):
        outdir = os.path.join("config", "preparation")
        os.makedirs(outdir, exist_ok=True)
        ids_path = os.path.join(outdir, "ids.txt")
        with open(ids_path, "w", encoding="utf-8") as f:
            f.write(ids_text.strip() + "\n")
        cmd = [
            "python", "tools/prepare_ticket_prompt.py",
            "--input", ids_path,
            "--outdir", outdir,
        ]
        if limit and limit > 0:
            cmd += ["--limit", str(limit)]
        if model:
            cmd += ["--model", model]
        if no_ai:
            cmd += ["--no-ai"]
        log_path = os.path.join(outdir, "last_run.log")
        with open(log_path, "w", encoding="utf-8") as log:
            try:
                subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            except Exception as e:
                log.write(f"Failed to start job: {e}\n")

    @app.post("/prep", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def prep_post(request: Request, ids: str = Form(""), limit: int = Form(0), model: str = Form(""), no_ai: Optional[bool] = Form(False)):
        if not ids.strip():
            return templates.TemplateResponse("prep.html", {"request": request, "message": "Please paste at least one ID."})
        threading.Thread(target=_run_prep, args=(ids, limit, model, bool(no_ai)), daemon=True).start()
        return templates.TemplateResponse("prep.html", {"request": request, "message": "Preparation started. See logs at config/preparation/last_run.log"})

    @app.get("/prep/log", response_class=HTMLResponse, dependencies=[Depends(basic_auth_dependency)])
    def prep_log(request: Request):
        log_path = os.path.join("config", "preparation", "last_run.log")
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()[-20000:]
        except FileNotFoundError:
            content = "No log yet. Start a preparation job."
        return templates.TemplateResponse("prep_log.html", {"request": request, "content": content})

    return app


app = create_app()
