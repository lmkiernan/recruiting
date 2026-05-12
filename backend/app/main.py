from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import candidates
from app.core.config import settings

app = FastAPI(title="Recruiter Signal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
