from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import candidates, evaluations, jobs
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Import all models so SQLAlchemy registers them before create_all
    import app.models.candidate  # noqa: F401
    import app.models.evaluation  # noqa: F401
    import app.models.job  # noqa: F401
    import app.models.shortlist  # noqa: F401
    import app.models.user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Recruiter Signal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router)
app.include_router(jobs.router)
app.include_router(evaluations.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
