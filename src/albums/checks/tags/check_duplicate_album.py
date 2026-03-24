from typing import override

from sqlalchemy import select
from sqlalchemy.orm import Session

from albums.app import Context
from albums.library.duplicates import DuplicateFinder
from albums.tagger.provider import AlbumTaggerProvider

from ...library.tag_tools import get_album_name_from_tags, get_artist_from_tags
from ...types import Album, CheckResult
from ..base_check import Check


class CheckDuplicateAlbum(Check):
    name = "duplicate-album"
    default_config = {"enabled": True}
    must_pass_checks = {"album-tag", "artist-tag"}
    _duplicates: DuplicateFinder

    def __init__(self, ctx: Context, tagger: AlbumTaggerProvider | None = None, session: Session | None = None):
        super().__init__(ctx, tagger, session)

        # tell user about the delay so the check can be disabled if unwanted
        with ctx.console.status(f"Initializing [bold]{self.name}[/bold] check [italic](disable check to skip)[/italic]", spinner="bouncingBar"):
            self._duplicates = DuplicateFinder(ctx, self.session)

    @override
    def check(self, album: Album) -> CheckResult | None:
        if not self.ctx.is_persistent:
            return None

        album_name = get_album_name_from_tags(album)
        artist = get_artist_from_tags(album)
        if not artist or not album_name:
            return None

        duplicate_ids = self._duplicates.find(self.ctx, self.session, artist, album_name, album.album_id)
        if not duplicate_ids:
            return None

        other_albums = select(Album).filter(Album.album_id.in_(duplicate_ids))
        paths = [a.path for (a,) in self.session.execute(other_albums).tuples()]
        return CheckResult(f"possible duplicate albums: {', '.join(f'"{path}"' for path in paths)}")
