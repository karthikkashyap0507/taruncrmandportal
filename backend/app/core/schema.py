"""Idempotent, additive schema migration, run at startup.

create_all() creates missing tables but never alters existing ones, so columns
and indexes added to the models later would never reach a live database. This
adds them. It never drops, renames or rewrites anything.
"""
import enum
import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _default_sql(col) -> str:
    if col.default is None or not getattr(col.default, "is_scalar", False):
        return ""
    val = col.default.arg
    if isinstance(val, enum.Enum):
        val = val.value
    if isinstance(val, bool):
        return f" DEFAULT {1 if val else 0}"
    if isinstance(val, (int, float)):
        return f" DEFAULT {val}"
    if isinstance(val, str):
        return " DEFAULT '" + val.replace("'", "''") + "'"
    return ""


def ensure_schema(engine, metadata) -> None:
    metadata.create_all(bind=engine)
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in metadata.sorted_tables:
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                ddl_type = col.type.compile(dialect=engine.dialect)
                conn.execute(text(
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl_type}{_default_sql(col)}'
                ))
                logger.info("schema: added column %s.%s", table.name, col.name)
    for table in metadata.sorted_tables:
        for index in table.indexes:
            try:
                index.create(bind=engine, checkfirst=True)
            except SQLAlchemyError as exc:
                # e.g. a unique index over rows that are already duplicated
                logger.warning("schema: could not create index %s: %s", index.name, exc)
