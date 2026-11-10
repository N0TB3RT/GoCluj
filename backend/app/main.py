from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import categories, events, ingest

app = FastAPI(title="GoCluj API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(categories.router)
app.include_router(ingest.router)
