"""
SQLAlchemy-ORM-Modelle für den a11y-Scanner.

Persistiert werden Jobs, gecrawlte Seiten, Findings sowie der Registry-Stand
eines Laufs (Reports bleiben so reproduzierbar).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    # pytest sammelt standardmäßig Klassen mit Namen "Test*" als Tests — die
    # ORM-Modelle (z. B. TestRecord) sollen nie als Tests behandelt werden.
    __test__ = False


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid
    url: Mapped[str] = mapped_column(Text)
    suite: Mapped[str] = mapped_column(String(32), default="bitv")
    # options: max_pages, htaccess_user, htaccess_pw, resolutions
    options: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(16), default="queued")
    # queued | running | done | failed | canceled
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    current_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pages: Mapped[list["Page"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    test_records: Mapped[list["TestRecord"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ok: Mapped[bool] = mapped_column(default=True)  # False bei 404/Netzwerkfehler
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="pages")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)

    test_id: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(Text)
    dom_path: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Denormalisierte Metadaten (aus dem Registry, Stand des Laufs)
    number: Mapped[str | None] = mapped_column(String(32), nullable=True)   # einzige Norm-Nummer (entry["id"])
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)  # WCAG | EN 301 549 | BITV
    level: Mapped[str] = mapped_column(String(16))        # MUSS/SOLLTE/KANN
    wcag_level: Mapped[str | None] = mapped_column(String(4), nullable=True)  # A/AA/AAA
    responsibility: Mapped[str] = mapped_column(String(32), default="technisch")
    priority: Mapped[str] = mapped_column(String(16), default="mittel")

    job: Mapped[Job] = relationship(back_populates="findings")


class TestRecord(Base):
    """Snapshot des Test-Registry-Stands für einen Job (Reproduzierbarkeit)."""

    __tablename__ = "test_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    test_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    suite: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))
    wcag_level: Mapped[str | None] = mapped_column(String(4), nullable=True)
    category: Mapped[str] = mapped_column(String(32))
    number: Mapped[str | None] = mapped_column(String(32), nullable=True)   # einzige Norm-Nummer (entry["id"])
    responsibility: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16))
    type: Mapped[str] = mapped_column(String(16))       # syntax|resolution|manual
    status: Mapped[str] = mapped_column(String(16))     # implemented|manual|nicht_relevant

    job: Mapped[Job] = relationship(back_populates="test_records")
