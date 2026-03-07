import logging
from typing import Generator, Sequence, TypedDict, Unpack

from sqlalchemy import Engine, and_, or_, select
from sqlalchemy.orm import Session, aliased

from ..types import Album
from .models import AlbumEntity, CollectionEntity, IgnoreCheckEntity, TrackEntity, TrackTagEntity
from .operations import album_to_album

logger = logging.getLogger(__name__)


class LoadOptions(TypedDict, total=False):
    load_track_tags: bool
    regex: bool

    collection: Sequence[str]
    path: Sequence[str]
    ignore_check: Sequence[str]
    tag: Sequence[str]


def load_albums(db: Engine, **kwargs: Unpack[LoadOptions]) -> Generator[Album, None, None]:
    load_track_tags = kwargs.get("load_track_tags", True)
    regex = kwargs.get("regex", False)
    with Session(db) as session:
        stmt = select(AlbumEntity)

        collection_names = kwargs.get("collection", [])
        if collection_names and regex:
            stmt = stmt.where(AlbumEntity.collections.any(and_(*(CollectionEntity.collection_name.regexp_match(c) for c in collection_names))))
        elif collection_names:
            stmt = stmt.where(AlbumEntity.collections.any(CollectionEntity.collection_name.in_(collection_names)))

        ignore_check_names = kwargs.get("ignore_check", [])
        if ignore_check_names and regex:
            stmt = stmt.where(AlbumEntity.ignore_checks.any(and_(*(IgnoreCheckEntity.check_name.regexp_match(c) for c in ignore_check_names))))
        elif ignore_check_names:
            stmt = stmt.where(AlbumEntity.ignore_checks.any(IgnoreCheckEntity.check_name.in_(ignore_check_names)))

        match_paths = kwargs.get("path", [])
        if match_paths and regex:
            stmt = stmt.where(or_(*(AlbumEntity.path.regexp_match(path_re) for path_re in match_paths)))
        elif match_paths:
            stmt = stmt.where(AlbumEntity.path.in_(match_paths))

        tags = kwargs.get("tag", [])
        if tags:
            stmt = stmt.distinct().join(TrackEntity, AlbumEntity.album_id == TrackEntity.album_id)
            for [name, value] in [t.split(":", 1) for t in tags]:
                entity = aliased(TrackTagEntity)
                if regex:
                    stmt = stmt.join(entity, and_(TrackEntity.track_id == entity.track_id, entity.name == name, entity.value.regexp_match(value)))
                else:
                    stmt = stmt.join(entity, and_(TrackEntity.track_id == entity.track_id, entity.name == name, entity.value == value))
        yield from (album_to_album(album[0], load_track_tags) for album in session.execute(stmt.order_by(AlbumEntity.path)))
