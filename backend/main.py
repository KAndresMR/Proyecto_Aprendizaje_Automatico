import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import engine, Base
from app.routes import inventory
from fastapi.middleware.cors import CORSMiddleware



# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI(
    title="Sistema de Gestión de Inventario",
    description="API para registro automático de productos con OCR",
    version="1.0.0",
    debug=settings.DEBUG
)

# --------------------------------------------------
# CORS - MUY IMPORTANTE
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔹 Temporalmente permitir todo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Startup
# --------------------------------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tablas de base de datos creadas/verificadas")

# --------------------------------------------------
# Static files
# --------------------------------------------------
app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads"
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
    return {
        "message": "Sistema de Gestión de Inventario API",
        "version": "1.0.0",
        "status": "running",
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}