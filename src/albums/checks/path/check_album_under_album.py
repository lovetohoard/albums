from sqlalchemy import and_, func, select

from ...types import Album, CheckResult
from ..base_check import Check
from ..helpers import album_display_name


class CheckAlbumUnderAlbum(Check):
    name = "album-under-album"
    default_config = {"enabled": True}

    def check(self, album: Album):
        path = album.path
        like_path = path.replace("|", "||").replace("%", "|%").replace("_", "|_") + "%"
        (matches,) = (
            self.session.execute(select(func.count("*")).select_from(Album).filter(and_(Album.path != path, Album.path.like(like_path, "|"))))
            .tuples()
            .one()
        )

        if matches > 0:
            return CheckResult(f"there are {matches} albums in directories under album {album_display_name(self.ctx, album)}")
