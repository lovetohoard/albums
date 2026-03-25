import glob
import logging
from collections import defaultdict
from itertools import chain
from pathlib import Path
from string import Template
from typing import Tuple

from pathvalidate import sanitize_filename, sanitize_filepath
from prompt_toolkit import choice
from prompt_toolkit.shortcuts import confirm
from rich.markup import escape
from sqlalchemy.orm import Session

from ..app import Context
from ..checks.checker import Checker
from ..library.duplicates import DuplicateFinder, album_in_library
from ..library.scanner import scan
from ..tagger.types import BasicTag
from ..types import Album
from .synchronizer import copy_files_with_progress

logger = logging.getLogger(__name__)


class Importer:
    ctx: Context
    _parent_context: Context
    _library: Path
    _extra: bool
    _recursive: bool
    _automatic: bool
    _duplicate_finder = DuplicateFinder()

    def __init__(self, child_context: Context, extra: bool, recursive: bool, automatic: bool):
        if child_context.parent is None:
            raise RuntimeError("Importer must be created in child context")

        self.ctx = child_context
        self._parent_context = child_context.parent
        self._library = child_context.config.library
        self._extra = extra
        self._recursive = recursive
        self._automatic = automatic

    def scan(self):
        (albums_total, _) = scan(self.ctx, check_first_full_scan_path_count=lambda ct: self._check_path_count(ct))
        if albums_total == 0:
            self.ctx.console.print(f"Album not found at {escape(str(self.ctx.config.library))}")
            raise SystemExit(1)
        if albums_total > 1 and self._recursive:
            self.ctx.console.print(
                f"THe [bold]--recursive[/bold] option cannot be used because there is more than one album at {escape(str(self.ctx.config.library))}"
            )
            raise SystemExit(1)
        with self.ctx.console.status("Initializing duplicate album finder", spinner="bouncingBar"):
            with Session(self._parent_context.db) as session:
                self._duplicate_finder.start(session)
        return albums_total

    def run(self):
        checker = Checker(self.ctx, self._automatic, preview=False, fix=False, interactive=True, show_ignore_option=True)
        non_interactive_checker = Checker(self.ctx, False, False, False, False, False)
        with Session(self.ctx.db) as session:
            for album in self.ctx.select_album_entities(session):
                (exists, ok) = self._check_existing_destination(album, self.make_library_paths(album))
                if not ok:
                    continue
                issues = 0
                quit = False
                self.ctx.select_album_entities = lambda _: iter([album])
                self.ctx.console.print(f"Starting import: {escape(album.path)}", highlight=False)
                while not quit and checker.run_enabled(session):
                    self.ctx.console.print("Remaining issues:")
                    issues = non_interactive_checker.run_enabled(session)
                    if issues == 0:
                        self.ctx.console.print("No issues")
                    quit = issues == 0 or confirm("There are still issues. Do you want to skip importing this album?")

                if not issues:
                    library_paths = self.make_library_paths(album)
                    if not exists:  # check again in case tag fixes changed the destination paths
                        (exists, ok) = self._check_existing_destination(album, library_paths)
                        if not ok:
                            continue
                    source_path = self.ctx.config.library / album.path
                    if self._automatic:
                        path_in_library = library_paths[0]
                    else:
                        options = [(album_path, f">> Copy to: {album_path}") for album_path in library_paths] + [("", ">> Cancel")]
                        path_in_library = choice(message=f"Ready to copy from {source_path}", options=options)
                    if path_in_library:
                        self.ctx.console.print(f"Import album from {source_path} to {str(self.ctx.config.library / path_in_library)}")
                        self.import_album(source_path, path_in_library, album)

    def _check_existing_destination(self, album: Album, library_paths: list[str]) -> Tuple[bool, bool]:
        # TODO check for duplicate album by tag values too
        existing = next((path for path in library_paths if (self._parent_context.config.library / path).exists()), None)
        if existing is None:
            existing = album_in_library(self.ctx, album)

        if existing is not None:
            self.ctx.console.print(f"This album appears to be in the library: [bold]{escape(existing)}[/bold]")
            if not self._automatic and confirm("Do you want to add it anyway?"):
                return (True, True)
            else:
                self.ctx.console.print("Skipping import")
                return (True, False)
        return (False, True)

    def _check_path_count(self, path_count: int) -> None:
        if path_count > self.ctx.config.import_scan_max_paths:
            self.ctx.console.print(
                f"found {path_count} paths, but import command is limited to {self.ctx.config.import_scan_max_paths} (controlled by global setting [bold]import_scan_max_paths[/bold])"
            )
            raise SystemExit(1)

    def import_album(self, source_path: Path, destination_path_in_library: str, album: Album):
        src = source_path.resolve()
        if not src.is_dir():
            logger.error(f"import_album: not a directory: {str(src)}")
            raise SystemExit(1)

        destination_path = self._parent_context.config.library / destination_path_in_library
        dest = Path(destination_path).resolve()
        if dest.exists():
            logger.error(f"import_album: destination already exists: {str(dest)}")
            raise SystemExit(1)
        if self._extra or self._recursive:
            filenames = glob.iglob("**", root_dir=src, recursive=self._recursive)
        else:
            filenames = chain((track.filename for track in sorted(album.tracks)), (file.filename for file in sorted(album.picture_files)))

        to_copy: list[tuple[Path, Path, int]] = []  # list of (source, destination, size)
        for filename in filenames:
            src_path = src / filename
            if src_path.is_file():
                to_copy.append((src_path, dest / filename, src_path.stat().st_size))
        if not to_copy:
            raise RuntimeError("unexpected: no files to copy?")

        copy_files_with_progress(self.ctx, to_copy)

        self.ctx.console.print(f"Imported album to {escape(destination_path_in_library)} (will be added to library on next scan)")
        # TODO add album to database immediately + include cover source mark or ignored checks from import process

    def make_library_paths(self, album: Album):
        used_identifiers = set(self.ctx.config.default_import_path.get_identifiers() + self.ctx.config.default_import_path_various.get_identifiers())
        used_identifiers.update(identifier for path_T in self.ctx.config.more_import_paths for identifier in path_T.get_identifiers())
        unknown_identifiers = used_identifiers - {"artist", "a1", "A1", "album"}
        if unknown_identifiers:
            logger.warning(f"ignoring unknown template identifiers in import path template: {', '.join(unknown_identifiers)}")

        tag_values: defaultdict[BasicTag, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        for track in album.tracks:
            for tag, values in ((k, v) for k, v in track.tag_dict().items() if k in {BasicTag.ALBUM, BasicTag.ALBUMARTIST, BasicTag.ARTIST}):
                for value in values:
                    tag_values[tag][value] += 1
        tag_values_by_freq = dict(
            (tag, sorted(((value, count) for value, count in value_map.items()), key=lambda vc: vc[1], reverse=True))
            for tag, value_map in tag_values.items()
        )
        artist_v = ""
        various = False
        using_artist = "artist" in used_identifiers or "A1" in used_identifiers or "a1" in used_identifiers

        def safe_path_element(folder: str) -> str:
            folder = folder.replace("/", self.ctx.config.path_replace_slash)
            return sanitize_filename(folder, replacement_text=self.ctx.config.path_replace_invalid, platform=self.ctx.config.path_compatibility)

        if BasicTag.ALBUMARTIST in tag_values_by_freq:
            albumartists = tag_values_by_freq[BasicTag.ALBUMARTIST]
            artist_v = safe_path_element(albumartists[0][0])
            if len(albumartists) > 1 and using_artist:
                logger.warning(f"generating library path: more than one album artist value, using {artist_v}")
            if len(tag_values_by_freq.get(BasicTag.ARTIST, [])) > 1:
                various = True
        elif BasicTag.ARTIST in tag_values_by_freq:
            artists = tag_values_by_freq[BasicTag.ARTIST]
            artist_v = safe_path_element(artists[0][0])
            if len(artists) > 1:
                various = True
                if using_artist:
                    logger.warning(f"generating library path: no album artist and more than one artist value, using {artist_v}")
        if not artist_v:
            artist_v = "Unknown Album"
            logger.warning(f"generating library path: no album artist or artist tags, using {artist_v}")

        album_v = ""
        if "album" in used_identifiers:
            if BasicTag.ALBUM in tag_values_by_freq:
                albums = tag_values_by_freq[BasicTag.ALBUM]
                album_v = safe_path_element(albums[0][0])
                if len(albums) > 1:
                    logger.warning(f"generating library path: more than one album artist value, using {album_v}")
            if not album_v:
                album_v = "Unknown Album"
                logger.warning(f"generating library path: no album artist or artist tags, using {artist_v}")

        a1_v = str.lower(safe_path_element(artist_v[4] if artist_v.lower().startswith("the ") and len(artist_v) > 4 else artist_v[0]))
        if a1_v.isnumeric():
            a1_v = "#"

        substitutions = {"album": album_v, "artist": artist_v, "a1": a1_v, "A1": a1_v.upper()}
        logger.debug(f"substitutions for creating import paths: {substitutions}")

        def make_path(template: Template) -> str:
            return sanitize_filepath(
                template.safe_substitute(substitutions),
                replacement_text=self.ctx.config.path_replace_invalid,
                platform=self.ctx.config.path_compatibility,
            )

        default = make_path(self.ctx.config.default_import_path)
        default_various = make_path(self.ctx.config.default_import_path_various)
        more = [make_path(path_T) for path_T in self.ctx.config.more_import_paths]
        return [default_various, *more, default] if various else [default, *more, default_various]
