import os
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

# Backend domain files (DB + routers)
from .backend.config import settings
from .backend.router_auth import router as auth_router
from .pacientes import router as pacientes_router
from .exames import router as exames_router
from experiments.greg_retina.greg_retina.router_laudos import router as laudos_router

# Inference script (already serves /predict + /status)
from experiments.greg_retina.greg_retina.greg_retina_inference import app as inference_app



BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR


def create_app() -> FastAPI:
    app = FastAPI(title="GREG Retinopatia — Backend", version="1.0.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers (auth/pacientes/exames/laudos) under same service
    app.include_router(auth_router)
    app.include_router(pacientes_router)
    app.include_router(exames_router)
    app.include_router(laudos_router)


    # Serve existing frontend HTML
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        # Mount static so browser can load any local assets if needed
        app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def home():
            return index_path.read_text(encoding="utf-8")

    # Never mount the entire directory as static.
    # Only serve the whitelisted frontend pages.

    @app.get("/login.html", response_class=HTMLResponse)
    async def login_page():
        login_path = BASE_DIR / "login.html"
        return login_path.read_text(encoding="utf-8") if login_path.exists() else HTMLResponse("Missing login.html", status_code=404)

    @app.get("/relatorio.html", response_class=HTMLResponse)
    async def relatorio_page():
        relatorio_path = BASE_DIR / "relatorio.html"
        return relatorio_path.read_text(encoding="utf-8") if relatorio_path.exists() else HTMLResponse("Missing relatorio.html", status_code=404)

    @app.get("/painel_pdfs.js")
    async def painel_pdfs_js():
        js_path = BASE_DIR / "painel_pdfs.js"
        return js_path.read_text(encoding="utf-8") if js_path.exists() else HTMLResponse("Missing painel_pdfs.js", status_code=404)

    @app.get("/health")
    async def api_health():
        return {"status": "ok"}

    @app.get("/backend/health")

    async def backend_health():
        return {"status": "ok"}

    # Expose inference endpoints on the same service by proxy-mounting.
    # Keep frontend contract: POST /predict and GET /status.
    #
    # We add only the needed routes from the inference_app.
    for route in inference_app.router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if path in ("/predict", "/status"):
            app.router.routes.append(route)


    # Also mount inference docs (optional): keep only if you want
    return app



# --- Minimal static auth guard for client-side pages ---
# This is handled by JS (login.html stores jwt in localStorage).
# Server-side protection is expected via API auth.

app = create_app()


