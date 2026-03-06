import os

from albums.app import Context
from albums.checks.path.check_duplicate_pathname import CheckDuplicatePathname
from albums.picture.info import PictureInfo
from albums.types import Album, PictureFile, Track


class TestCheckDuplicatePathname:
    def test_pathname_ok(self):
        album = Album(
            "Foo" + os.sep,
            [Track("normal.1.flac"), Track("normal.2.flac")],
            [],
            [],
            [
                PictureFile("normal.jpg", PictureInfo("image/jpeg", 1, 1, 1, 1, b""), 0, False),
                PictureFile("normal.png", PictureInfo("image/png", 1, 1, 1, 1, b""), 0, False),
            ],
        )
        assert not CheckDuplicatePathname(Context()).check(album)

    def test_pathname_duplicate_picture_file(self):
        album = Album(
            "Foo" + os.sep,
            [Track("normal.1.flac"), Track("normal.2.flac")],
            [],
            [],
            [
                PictureFile("FileName.jpg", PictureInfo("image/jpeg", 1, 1, 1, 1, b""), 0, False),
                PictureFile("Filename.jpg", PictureInfo("image/jpeg", 1, 1, 1, 1, b""), 0, False),
            ],
        )
        result = CheckDuplicatePathname(Context()).check(album)
        assert result is not None
        assert "2 files are variations of filename.jpg" in result.message

    def test_pathname_duplicate_track_file(self):
        album = Album(
            "Foo" + os.sep,
            [Track("track.flac"), Track("Track.flac")],
            [],
            [],
            [
                PictureFile("normal.jpg", PictureInfo("image/jpeg", 1, 1, 1, 1, b""), 0, False),
                PictureFile("normal.png", PictureInfo("image/png", 1, 1, 1, 1, b""), 0, False),
            ],
        )
        result = CheckDuplicatePathname(Context()).check(album)
        assert result is not None
        assert "2 files are variations of track.flac" in result.message
