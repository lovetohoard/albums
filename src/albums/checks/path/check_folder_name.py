from collections import defaultdict
from os import rename, sep
from pathlib import Path
from string import Template
from typing import Any

from pathvalidate import sanitize_filename
from rich.markup import escape

from ...tagger.types import BasicTag
from ...types import Album, CheckResult, Fixer
from ..base_check import Check


class CheckFolderName(Check):
    name = "folder-name"
    default_config = {"enabled": True, "format": "$album"}
    must_pass_checks = {"album-tag", "artist-tag"}

    def init(self, check_config: dict[str, Any]):
        self.format = Template(check_config.get("format", self.default_config["format"]))
        for id in self.format.get_identifiers():
            if id not in {"artist", "album"}:
                raise ValueError(f"invalid substitution '{id}' in folder-name.format")

    def check(self, album: Album):
        if not self._can_generate_folder_name(album):
            return None  # TODO: configure behavior when album doesn't have tags to generate folder name

        correct_name = self._generate_folder_name(album)
        if Path(album.path).name == correct_name:
            return None

        new_path = (self.ctx.config.library / album.path).parent / correct_name
        if new_path.exists():
            return CheckResult(f"folder name does not match pattern, but new path already exists: {Path(album.path).parent / correct_name}")

        options = [f'>> Rename folder to "{escape(correct_name)}"']
        option_automatic_index = 0
        return CheckResult(
            f'folder name does not match pattern, should be "{escape(correct_name)}"',
            Fixer(lambda option: self._fix_use_generated(album), options, False, option_automatic_index),
        )

    def _fix_use_generated(self, album: Album):
        new_path_str = str(Path(album.path).parent / self._generate_folder_name(album))
        old_path = self.ctx.config.library / album.path
        if str.lower(new_path_str) == str.lower(album.path):
            # extra step for case-only rename
            num = 0
            while (temp := old_path.with_suffix(f".{num}")) and temp.exists():
                num += 1
            self.ctx.console.print(f"Temporarily renaming {escape(album.path)} to {escape(temp.name)}", highlight=False)
            rename(old_path, temp)
            old_path = temp

        self.ctx.console.print(f"Renaming {escape(old_path.name)} to {escape(new_path_str)}", highlight=False)
        rename(old_path, self.ctx.config.library / new_path_str)
        album.path = new_path_str + sep
        return True

    def _can_generate_folder_name(self, album: Album) -> bool:
        ids = self.format.get_identifiers()
        if "album" in ids and not any(t.has(BasicTag.ALBUM) for t in album.tracks):
            return False
        if "artist" in ids and not any(t.has(BasicTag.ARTIST) or t.has(BasicTag.ALBUMARTIST) for t in album.tracks):
            return False
        return True

    def _generate_folder_name(self, album: Album) -> str:
        artists: defaultdict[str, int] = defaultdict(int)
        album_names: defaultdict[str, int] = defaultdict(int)
        for track in album.tracks:
            for artist in track.get(BasicTag.ARTIST, []):
                artists[artist] += 1
            for albumartist in track.get(BasicTag.ALBUMARTIST, []):
                artists[albumartist] += 1
            for album_name in track.get(BasicTag.ALBUM, []):
                album_names[album_name] += 1
        artist_list = sorted(((k, v) for k, v in artists.items()), key=lambda i: i[1], reverse=True)
        artist = artist_list[0][0] if len(artist_list) else "Unknown Artist"
        album_name_list = sorted(((k, v) for k, v in album_names.items()), key=lambda i: i[1], reverse=True)
        album_name = album_name_list[0][0] if len(album_name_list) else "Unknown Album"
        folder_name = self.format.safe_substitute({"artist": artist, "album": album_name})
        folder_name = folder_name.replace("/", self.ctx.config.path_replace_slash)
        folder_name = sanitize_filename(
            folder_name, replacement_text=self.ctx.config.path_replace_invalid, platform=self.ctx.config.path_compatibility
        )
        return folder_name
