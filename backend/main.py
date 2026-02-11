import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import engine, Base
from backend.app.api import inventory

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Lifespan (startup / shutdown)
# --------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la app"""
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tablas de base de datos creadas")
    yield
    # Shutdown
    logger.info("🛑 Aplicación detenida")

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI(
    title="Agente de Inventario IA",
    version="1.0.0",
    #debug=settings.DEBUG,
    lifespan=lifespan
)

# --------------------------------------------------
# CORS - MUY IMPORTANTE
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Routes
# --------------------------------------------------
app.include_router(inventory.router)

# --------------------------------------------------
# Health / Root
# --------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "Agente Inventario IA"}


from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")