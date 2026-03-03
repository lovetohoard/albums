import logging
import sqlite3
import sys
from pathlib import Path

import humanize

from .schema import SQL_INIT_SCHEMA, migrate

logger = logging.getLogger(__name__)

MEMORY = ":memory:"

SQL_INIT_CONNECTION = """
PRAGMA foreign_keys = ON;
"""

SQL_CLEANUP = "DELETE FROM collection WHERE collection_id NOT IN (SELECT collection_id FROM album_collection);"


def open(filename: str | Path):
    in_memory = filename == MEMORY
    new_database = in_memory or not Path(filename).exists()

    db = sqlite3.connect(filename, autocommit=True)
    try:
        db.executescript(SQL_INIT_CONNECTION)
        _maintain(db)
        db.autocommit = False

        if new_database:
            if not in_memory:
                print(f"creating database {filename}")
            with db:
                db.executescript(SQL_INIT_SCHEMA)

        migrate(db, in_memory)
        with db:
            db.executescript(SQL_CLEANUP)

        return db
    except Exception as ex:
        db.close()
        raise ex


def close(db: sqlite3.Connection):
    db.close()
    logger.debug("closed database")


def _maintain(db: sqlite3.Connection):
    [page_size, page_count, freelist_count] = db.execute(
        "SELECT page_size, page_count, freelist_count FROM pragma_page_size, pragma_page_count, pragma_freelist_count;"
    ).fetchall()[0]
    size = page_size * page_count
    wasted = page_size * freelist_count
    logger.debug(f"database size approx {humanize.naturalsize(size, binary=True)} (wasted space approx {humanize.naturalsize(wasted, binary=True)})")
    # if wasted space is > 10 MB or 20% of the total size, vacuum
    if wasted > max(10 * 1024 * 1024, 0.2 * size):
        logger.debug("vacuuming database")
        db.execute("VACUUM;")


if __name__ == "__main__":
    open(sys.argv[1]).close()  # create empty database for diagram
