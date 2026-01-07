from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="LinkedIn Outreach Agent",
    description="Automation agent for LinkedIn outreach",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "LinkedIn Outreach Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": settings.app_env}