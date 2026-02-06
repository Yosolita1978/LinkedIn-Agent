from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import upload_router, contacts_router

# Import models so SQLAlchemy knows about them before creating tables
from app.models import (
    Contact,
    Message,
    ResurrectionOpportunity,
    TargetCompany,
    OutreachQueueItem,
    DataUpload,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="LinkedIn Intelligence & Outreach Agent",
    description="Personal intelligence tool for strategic LinkedIn outreach",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload_router)
app.include_router(contacts_router)


@app.get("/")
async def root():
    return {"message": "LinkedIn Intelligence & Outreach Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": settings.app_env}
