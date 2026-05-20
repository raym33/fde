"""Modelos SQLAlchemy (producción).

Multi-tenancy: cada fila lleva `tenant_id`. Para `chunks` se recomienda además
Row-Level Security (RLS) en Postgres y/o colección/esquema dedicado por tenant
para clientes enterprise. La columna `embedding` usa el tipo `vector` de
pgvector; crea un índice HNSW para búsqueda por similitud.

Migraciones: gestiónalas con Alembic (no incluido en el scaffold).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:  # pgvector solo disponible en producción
    from pgvector.sqlalchemy import Vector

    _EMBED_DIM = 1024  # ajusta a la dimensión de tu modelo de embeddings
    EmbeddingType = Vector(_EMBED_DIM)
except Exception:  # pragma: no cover
    EmbeddingType = JSON  # fallback inocuo para entornos sin pgvector


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    data_region: Mapped[str] = mapped_column(String(8), default="eu")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    sensitivity: Mapped[str] = mapped_column(String(32), default="internal")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )


class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(EmbeddingType)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    __table_args__ = (
        Index("ix_chunks_tenant", "tenant_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
