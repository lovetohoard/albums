import mimetypes

_IMAGE_MODE_BPP = {
    "1": 1,
    "L": 8,
    "P": 8,
    "RGB": 24,
    "RGBA": 32,
    "CMYK": 32,
    "YCbCr": 24,
    "LAB": 24,
    "HSV": 24,
    "I": 32,
    "F": 32,
    "I;16": 16,
    "I;16B": 16,
    "I;16L": 16,
    "I;16N": 16,
    "LA": 16,
    "PA": 16,
    "RGBX": 32,
}


def get_depth_bpp(pillow_mode: str, guess: int = 24):
    if pillow_mode in _IMAGE_MODE_BPP:
        return _IMAGE_MODE_BPP[pillow_mode]
    return guess


_MIME_PILLOW_FORMAT = {
    "image/bmp": "BMP",
    "image/gif": "GIF",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/tiff": "TIFF",
    "image/vnd.zbrush.pcx": "PCX",
    "image/webp": "WEBP",
}
_PILLOW_FORMAT_MIME = dict((pillow, mime) for mime, pillow in _MIME_PILLOW_FORMAT.items())

# Can add any extension if format is autodetected by Pillow and ".<FORMAT>" is a file extension supported by mimetypes.guess_type
SUPPORTED_IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jpeg", ".jpg", ".pcx", ".png", ".tif", ".tiff", ".webp"})
SUPPORTED_IMAGE_MIME_TYPES = frozenset(_MIME_PILLOW_FORMAT.keys())


def mime_type_to_format(mime_type: str) -> str:
    return _MIME_PILLOW_FORMAT[mime_type]


def format_to_mime_type(image_format: str) -> str:
    mime_type, _ = mimetypes.guess_type(f"_.{image_format}")
    return mime_type or _PILLOW_FORMAT_MIME[str.upper(image_format)]
