from collections import defaultdict
from typing import Sequence, override

from sqlalchemy import select

from ...library.tag_tools import get_album_name_from_tags, get_artist_from_tags
from ...types import Album, CheckResult
from ..base_check import Check


class CheckDuplicateAlbum(Check):
    name = "duplicate-album"
    default_config = {"enabled": True}
    must_pass_checks = {"album-tag", "artist-tag"}
    _duplicates: dict[tuple[str, str], list[int]] | None = None

    @override
    def check(self, album: Album) -> CheckResult | None:
        album_name = get_album_name_from_tags(album)
        artist = get_artist_from_tags(album)
        if artist and album_name:
            duplicate_ids = self._check_duplicates(artist, album_name)
            if duplicate_ids:
                other_albums = select(Album).filter(Album.album_id.in_(id for id in duplicate_ids if id != album.album_id))
                paths = [a.path for (a,) in self.session.execute(other_albums).tuples()]
                return CheckResult(f"possible duplicate albums: {', '.join(f'"{path}"' for path in paths)}")

    def _check_duplicates(self, artist: str, album_name: str) -> Sequence[int] | None:
        # this takes several seconds on a large library, but when checking the whole library, this way is 6x faster than querying per album
        if self._duplicates is None:
            self._duplicates = self._init_duplicates()
        # TODO: try variants (without parenthetical, without articles) and/or match "similar" strings
        return self._duplicates.get((str.lower(artist), str.lower(album_name)))

    def _init_duplicates(self):
        # tell user about the delay so the check can be disabled if unwanted
        with self.ctx.console.status(f"Initializing [bold]{self.name}[/bold] check [italic](disable check to skip)[/italic]", spinner="bouncingBar"):
            albums: defaultdict[tuple[str, str], list[int]] = defaultdict(list[int])
            for (album,) in self.session.execute(select(Album)).tuples():
                add_album_name = get_album_name_from_tags(album)
                add_artist = get_artist_from_tags(album)
                if add_album_name and add_artist and album.album_id is not None:
                    albums[(str.lower(add_artist), str.lower(add_album_name))].append(album.album_id)
            return dict((k, ids) for k, ids in albums.items() if len(ids) > 1)
