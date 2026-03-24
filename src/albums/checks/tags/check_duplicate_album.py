from itertools import chain
from typing import Sequence, override

import humanize
from rich.console import RenderableType
from rich.markup import escape
from sqlalchemy import select
from sqlalchemy.orm import Session

from albums.app import Context
from albums.library.duplicates import DuplicateFinder
from albums.tagger.provider import AlbumTaggerProvider

from ...library.tag_tools import get_album_name_from_tags, get_artist_from_tags
from ...types import Album, CheckResult, Fixer, OtherFile, PictureFile, Track
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

        other_albums = [a for (a,) in self.session.execute(select(Album).filter(Album.album_id.in_(duplicate_ids))).tuples()]
        if len(other_albums) > 1:
            return CheckResult(f"multiple possible duplicate albums: {', '.join(f'"{a.path}"' for a in other_albums)}")

        other = other_albums[0]
        options: list[str] = []
        option_automatic_index = None
        this_tracks = sorted(album.tracks)
        other_tracks = sorted(other.tracks)
        rows: list[list[RenderableType]] = [[*self._summarize(album), *self._summarize(other)], [""] * 4]
        rows.extend(
            [self._filename(this_tracks, ix), self._desc(this_tracks, ix), self._filename(other_tracks, ix), self._desc(other_tracks, ix)]
            for ix in range(0, max(len(this_tracks), len(other_tracks)))
        )
        this_more = sorted(album.picture_files + album.other_files)
        other_more = sorted(other.picture_files + other.other_files)
        if len(this_more) + len(other_more):
            rows.extend([[""] * 4, ["[italic]other files (scanned files only)[/italic]", ""] * 2])
            rows.extend(
                [self._filename(this_more, ix), self._desc(this_more, ix), self._filename(other_more, ix), self._desc(other_more, ix)]
                for ix in range(0, max(len(this_more), len(other_more)))
            )
        table = ([f'This album: "{escape(album.path)}"', "files", f'Other album: "{other.path}"', "files"], rows)
        return CheckResult(
            f"possible duplicate albums: {', '.join(f'"{a.path}"' for a in other_albums)}",
            Fixer(lambda _: False, options, False, option_automatic_index, table),
        )

    def _summarize(self, album: Album) -> tuple[str, str]:
        track_codecs = set(t.stream.codec for t in album.tracks)
        codec = "[bold]multiple codecs[/bold]" if len(track_codecs) > 1 else track_codecs.pop()
        bitrate = f"{int(sum(t.stream.bitrate for t in album.tracks) / len(album.tracks) / 1024)}kbps"

        time = _min_sec(sum(t.stream.length for t in album.tracks))
        size = humanize.naturalsize(sum(f.file_size for f in chain(album.tracks, album.picture_files, album.other_files)))

        return (f"[italic]{len(album.tracks)} tracks {codec} ~{bitrate} {time}[/italic]", size)

    def _filename(self, files: Sequence[Track | PictureFile | OtherFile], ix: int) -> str:
        return escape(files[ix].filename) if ix < len(files) else ""

    def _desc(self, files: Sequence[Track | PictureFile | OtherFile], ix: int) -> str:
        if ix >= len(files):
            return ""

        file = files[ix]
        time = f"{_min_sec(file.stream.length)} " if isinstance(file, Track) else ""
        return f"{time}{humanize.naturalsize(file.file_size)}"


def _min_sec(secs: float | int) -> str:
    return "{:02}m{:02}s".format(*divmod(int(secs), 60))
