from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import REAL, Boolean, Column, Dialect, ForeignKey, Index, Integer, LargeBinary, Table, Text, TypeDecorator, text
from sqlalchemy.orm import DeclarativeBase, Mapped, composite, mapped_column, relationship

from ..picture.info import PictureInfo
from ..tagger.types import PictureType, StreamInfo


class Base(DeclarativeBase):
    pass


schema_table = Table("_schema", Base.metadata, Column("version", Integer, nullable=False, unique=True))


album_collection_association_table = Table(
    "album_collection",
    Base.metadata,
    Column[int]("album_id", ForeignKey("album.album_id")),
    Column[int]("collection_id", ForeignKey("collection.collection_id")),
)


class AlbumEntity(Base):
    __tablename__ = "album"
    __table_args__ = (Index("album_path", "path", unique=True),)

    album_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)

    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    scanner: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    collections: Mapped[list[CollectionEntity]] = relationship(secondary=album_collection_association_table, back_populates="albums")
    ignore_checks: Mapped[list[IgnoreCheckEntity]] = relationship("IgnoreCheckEntity", back_populates="album")
    picture_files: Mapped[list[PictureFileEntity]] = relationship("PictureFileEntity", back_populates="album")
    tracks: Mapped[list[TrackEntity]] = relationship("TrackEntity", back_populates="album")


class CollectionEntity(Base):
    __tablename__ = "collection"

    collection_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)
    collection_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    albums: Mapped[list[AlbumEntity]] = relationship(secondary=album_collection_association_table, back_populates="collections")


class ScanHistoryEntity(Base):
    __tablename__ = "scan_history"
    __table_args__ = (Index("idx_scan_history_timestamp", "timestamp"),)

    scan_history_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)

    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    folders_scanned: Mapped[int] = mapped_column(Integer, nullable=False)
    albums_total: Mapped[int] = mapped_column(Integer, nullable=False)


class SettingEntity(Base):
    __tablename__ = "setting"

    name: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)  # TODO parse and map to Union[str, int, float, bool, Sequence[str]]


class IgnoreCheckEntity(Base):
    __tablename__ = "album_ignore_check"
    __table_args__ = (Index("idx_ignore_check_album_id", "album_id"),)

    album_ignore_check_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)

    check_name: Mapped[str] = mapped_column(Text, nullable=False)
    album_id: Mapped[Optional[int]] = mapped_column(ForeignKey("album.album_id"))

    album: Mapped[Optional[AlbumEntity]] = relationship("AlbumEntity", back_populates="ignore_checks")


class PictureFileEntity(Base):
    __tablename__ = "album_picture_file"
    __table_args__ = (Index("idx_album_picture_file_album_id", "album_id"),)

    album_picture_file_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)
    album_id: Mapped[Optional[int]] = mapped_column(ForeignKey("album.album_id"))

    filename: Mapped[str] = mapped_column(Text, nullable=False)
    modify_timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    cover_source: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    load_issue: Mapped[Optional[str]] = mapped_column(Text)  # TODO parse and map to Tuple[Tuple[str, str | int], ...]

    _format: Mapped[str] = mapped_column("format", Text, nullable=False)
    _width: Mapped[int] = mapped_column("width", Integer, nullable=False)
    _height: Mapped[int] = mapped_column("height", Integer, nullable=False)
    _depth_bpp: Mapped[int] = mapped_column("depth_bpp", Integer, nullable=False)
    _file_size: Mapped[int] = mapped_column("file_size", Integer, nullable=False)
    _file_hash: Mapped[bytes] = mapped_column("file_hash", LargeBinary, nullable=False)
    file_info = composite(PictureInfo, _format, _width, _height, _depth_bpp, _file_size, _file_hash)

    album: Mapped[Optional[AlbumEntity]] = relationship("AlbumEntity", back_populates="picture_files")


class TrackEntity(Base):
    __tablename__ = "track"
    __table_args__ = (Index("idx_track_album_id", "album_id"),)

    track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)
    album_id: Mapped[Optional[int]] = mapped_column(ForeignKey("album.album_id"))

    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    modify_timestamp: Mapped[int] = mapped_column(Integer, nullable=False)

    _stream_length: Mapped[float] = mapped_column("stream_length", REAL, nullable=False)
    _stream_bitrate: Mapped[int] = mapped_column("stream_bitrate", Integer, nullable=False)
    _stream_channels: Mapped[int] = mapped_column("stream_channels", Integer, nullable=False)
    _stream_codec: Mapped[str] = mapped_column("stream_codec", Text, nullable=False)
    _stream_sample_rate: Mapped[int] = mapped_column("stream_sample_rate", Integer, nullable=False)
    stream = composite(StreamInfo, _stream_length, _stream_bitrate, _stream_channels, _stream_codec, _stream_sample_rate)

    album: Mapped[Optional[AlbumEntity]] = relationship("AlbumEntity", back_populates="tracks")
    pictures: Mapped[list[TrackPictureEntity]] = relationship("TrackPictureEntity", back_populates="track")
    tags: Mapped[list[TrackTagEntity]] = relationship("TrackTagEntity", back_populates="track")


class IntEnum[EnumType](TypeDecorator[EnumType]):
    impl = Integer

    def __init__(self, enum_type: type, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._enum_type = enum_type

    def process_bind_param(self, value: EnumType | None, dialect: Dialect):  # pyright: ignore[reportUnknownParameterType]
        return None if value is None else value.value  # type: ignore

    def process_result_value(self, value: int | None, dialect: Dialect):
        return self._enum_type(value)


class TrackPictureEntity(Base):
    __tablename__ = "track_picture"
    __table_args__ = (Index("idx_track_picture_track_id", "track_id"),)

    track_picture_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)
    track_id: Mapped[Optional[int]] = mapped_column(ForeignKey("track.track_id"))

    picture_type: Mapped[PictureType] = mapped_column(IntEnum[PictureType](PictureType), nullable=False)
    embed_ix: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    load_issue: Mapped[Optional[str]] = mapped_column(Text)

    _format: Mapped[str] = mapped_column("format", Text, nullable=False)
    _width: Mapped[int] = mapped_column("width", Integer, nullable=False)
    _height: Mapped[int] = mapped_column("height", Integer, nullable=False)
    _depth_bpp: Mapped[int] = mapped_column("depth_bpp", Integer, nullable=False)
    _file_size: Mapped[int] = mapped_column("file_size", Integer, nullable=False)
    _file_hash: Mapped[bytes] = mapped_column("file_hash", LargeBinary, nullable=False)
    file_info = composite(PictureInfo, _format, _width, _height, _depth_bpp, _file_size, _file_hash)

    track: Mapped[Optional[TrackEntity]] = relationship("TrackEntity", back_populates="pictures")


class TrackTagEntity(Base):
    __tablename__ = "track_tag"
    __table_args__ = (Index("idx_track_tag_track_id", "track_id"),)

    track_tag_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, primary_key=True)
    track_id: Mapped[Optional[int]] = mapped_column(ForeignKey("track.track_id"))

    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    track: Mapped[Optional[TrackEntity]] = relationship("TrackEntity", back_populates="tags")
