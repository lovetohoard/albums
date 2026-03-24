from collections import defaultdict
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from albums.app import Context
from albums.library.tag_tools import get_album_name_from_tags, get_artist_from_tags
from albums.types import Album


class DuplicateFinder:
    _duplicates: dict[tuple[str, str], list[int]]

    def __init__(self, ctx: Context, session: Session):
        # this takes several seconds on a large library, but when checking the whole library, this way is 6x faster than querying per album
        albums: defaultdict[tuple[str, str], list[int]] = defaultdict(list[int])
        for (album,) in session.execute(select(Album).order_by(Album.path)).tuples():
            add_album_name = get_album_name_from_tags(album)
            add_artist = get_artist_from_tags(album)
            if add_album_name and add_artist and album.album_id is not None:
                albums[(str.lower(add_artist), str.lower(add_album_name))].append(album.album_id)
        self._duplicates = dict((k, ids) for k, ids in albums.items() if len(ids) > 1)

    def find(self, ctx: Context, session: Session, artist: str, album_name: str, album_id: int | None = None) -> Sequence[int] | None:
        # TODO: try variants (without parenthetical, without articles) and/or match "similar" strings
        ids = self._duplicates.get((str.lower(artist), str.lower(album_name)))
        if ids is None or (album_id is not None and ids[0] != album_id):
            return None
        return ids[1:]

    def remove(self, ctx: Context, session: Session, artist: str, album_name: str, album_id: int):
        ids = self._duplicates.get((str.lower(artist), str.lower(album_name)), [])
        if album_id in ids:
            ids.remove(album_id)
        else:
            raise ValueError(f"error, cannot remove duplicate album {album_id} ({artist}/{album_name}) because it was not found")
