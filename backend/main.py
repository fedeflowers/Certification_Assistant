"""
Certification Assistant Backend - FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.config import settings
from shared.database import init_db
from shared.cache import init_redis

from certifications.routes import router as certifications_router
from quiz.routes import router as quiz_router
from analytics.routes import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and cleanup on shutdown."""
    # Initialize database
    await init_db()
    
    # Initialize Redis
    await init_redis()
    
    yield
    
    # Cleanup resources on shutdown
    from shared.cache import close_redis
    await close_redis()


app = FastAPI(
    title="Certification Assistant API",
    description="Backend API for the Certification Assistant application",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving images
app.mount("/api/images", StaticFiles(directory=f"{settings.data_path}/images"), name="images")

# Include routers
app.include_router(certifications_router, prefix="/api/certifications", tags=["certifications"])
app.include_router(quiz_router, prefix="/api/quiz", tags=["quiz"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Certification Assistant API", "docs": "/docs"}
