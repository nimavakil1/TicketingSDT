from __future__ import annotations

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os

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
    app = FastAPI(title="AI Support Admin", root_path=os.getenv("ADMIN_ROOT_PATH", "/TicketingSDT"))

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

    return app


app = create_app()
