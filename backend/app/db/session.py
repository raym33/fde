"""Sesión asíncrona de SQLAlchemy (producción).

En DEMO_MODE no se usa BD. Importa estas utilidades solo cuando demo_mode=False.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from app.config import get_settings

_engine = None
_sessionmaker = None


def _init():
    global _engine, _sessionmaker
    if _sessionmaker is None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


@asynccontextmanager
async def get_session():
    sm = _init()
    async with sm() as session:
        yield session
