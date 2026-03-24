import os

from albums.app import Context, Session
from albums.checks.tags.check_duplicate_album import CheckDuplicateAlbum
from albums.database import connection
from albums.types import Album, BasicTag, Track


class TestCheckDuplicateAlbum:
    def test_duplicate_ok(self):
        albums = [
            Album(path="one" + os.sep, tracks=[Track(filename="1.flac", tag={BasicTag.ALBUM: "The One", BasicTag.ARTIST: "Foo"})]),
            Album(path="two" + os.sep, tracks=[Track(filename="1.flac", tag={BasicTag.ALBUM: "Two", BasicTag.ARTIST: "Foo"})]),
        ]
        ctx = Context()
        ctx.db = connection.open(connection.MEMORY)
        with Session(ctx.db) as session:
            session.add(albums[0])
            session.add(albums[1])
            session.flush()
            assert albums[0].album_id
            assert not CheckDuplicateAlbum(ctx).check(albums[0])
            assert not CheckDuplicateAlbum(ctx).check(albums[1])

    def test_duplicate_exact(self):
        albums = [
            Album(path="One (2001)" + os.sep, tracks=[Track(filename="1.flac", tag={BasicTag.ALBUM: "The One", BasicTag.ARTIST: "Foo"})]),
            Album(path="One!" + os.sep, tracks=[Track(filename="1.flac", tag={BasicTag.ALBUM: "The One", BasicTag.ARTIST: "Foo"})]),
        ]
        ctx = Context()
        ctx.db = connection.open(connection.MEMORY)
        with Session(ctx.db) as session:
            session.add(albums[0])
            session.add(albums[1])
            session.flush()

            assert albums[0].album_id
            result = CheckDuplicateAlbum(ctx).check(albums[0])
            assert result
            assert 'possible duplicate albums: "One!' in result.message
            assert not result.fixer

            result = CheckDuplicateAlbum(ctx).check(albums[1])
            assert result
            assert 'possible duplicate albums: "One (2001)' in result.message
            assert not result.fixer

    def test_duplicate_case_insensitive(self):
        albums = [
            Album(path="One at a Time" + os.sep, tracks=[Track(filename="1.flac", tag={BasicTag.ALBUM: "One at a Time", BasicTag.ARTIST: "Foo"})]),
            Album(path="One At A Time" + os.sep, tracks=[Track(filename="1.flac", tag={BasicTag.ALBUM: "One At A Time", BasicTag.ARTIST: "Foo"})]),
        ]
        ctx = Context()
        ctx.db = connection.open(connection.MEMORY)
        with Session(ctx.db) as session:
            session.add(albums[0])
            session.add(albums[1])
            session.flush()

            assert albums[0].album_id
            result = CheckDuplicateAlbum(ctx).check(albums[0])
            assert result
            assert 'possible duplicate albums: "One At A Time' in result.message
            assert not result.fixer

            result = CheckDuplicateAlbum(ctx).check(albums[1])
            assert result
            assert 'possible duplicate albums: "One at a Time' in result.message
            assert not result.fixer

    def test_duplicate_compilation(self):
        albums = [
            Album(
                path="Lots" + os.sep,
                tracks=[
                    Track(filename="2.flac", tag={BasicTag.ALBUM: "Lots", BasicTag.ARTIST: "Bar", BasicTag.ALBUMARTIST: "Various Artists"}),
                    Track(filename="1.flac", tag={BasicTag.ALBUM: "Lots", BasicTag.ARTIST: "Foo", BasicTag.ALBUMARTIST: "Various Artists"}),
                ],
            ),
            Album(
                path="Lots (2000)" + os.sep,
                tracks=[
                    Track(filename="1.flac", tag={BasicTag.ALBUM: "Lots", BasicTag.ARTIST: "Foo", BasicTag.ALBUMARTIST: "Various Artists"}),
                    Track(filename="2.flac", tag={BasicTag.ALBUM: "Lots", BasicTag.ARTIST: "Bar", BasicTag.ALBUMARTIST: "Various Artists"}),
                ],
            ),
        ]
        ctx = Context()
        ctx.db = connection.open(connection.MEMORY)
        with Session(ctx.db) as session:
            session.add(albums[0])
            session.add(albums[1])
            session.flush()

            assert albums[0].album_id
            result = CheckDuplicateAlbum(ctx).check(albums[0])
            assert result
            assert 'possible duplicate albums: "Lots (2000)' in result.message
            assert not result.fixer

            result = CheckDuplicateAlbum(ctx).check(albums[1])
            assert result
            assert f'possible duplicate albums: "Lots{os.sep}' in result.message
            assert not result.fixer
