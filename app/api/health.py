"""Health endpoint: reports whether the app is up and the database is reachable."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health(session: Session = Depends(get_db_session)) -> JSONResponse:
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("database health check failed")
        return JSONResponse(status_code=503, content={"status": "degraded", "db": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ok", "db": "connected"})
