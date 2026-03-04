# albums

Manage a library of music: validate and fix tags and metadata, rename files,
adjust and embed album art, clean up and import albums, and sync parts of the
library to digital audio players or portable storage

- [Read the documentation here](https://4levity.github.io/albums/)

## Overview

`albums` works with media files and tags, but primarily acts on "albums" rather
than individual files. Everything is done locally and an Internet connection is
not required. It's a command-line app but it is designed to be user friendly,
with interactive menus, rich text formatting, tables and even blocky graphics.

It can work with a single folder or scan a whole media library into its database
to make subsequent operations fast. It has
[many automated checks and fixes](https://4levity.github.io/albums/all_checks/)
for metadata related issues such as track numbering (sequence, totals, disc
numbers), album-artist tags, embedding cover art, etc. It supports marking
albums as part of "collections," for example to make a list of albums to sync to
a digital audio player. It can also perform the sync.

## Why use `albums` instead of other music library tools?

Use them all, you don't have to decide. If you have missing metadata or
unidentified recordings and you want to use online databases to fill in the
blanks, [MusicBrainz Picard](https://picard.musicbrainz.org/) is good for that.
For editing tags with some fancy features and automation,
[puddletag](https://docs.puddletag.net/#) and
[MP3TAG](https://www.mp3tag.de/en/index.html) (proprietary but no cost for
Windows version) are nice, while [EasyTAG](https://wiki.gnome.org/Apps/EasyTAG)
is simple and quick.

The purpose of `albums` is finding and fixing metadata problems, resolving
inconsistencies and applying your preferred policies so that standard tags,
cover art, filenames are just right. `albums` has many individually configured
"checks" to find and sometimes automatically fix problems. You can review each
change, or only the ones that require a choice. The documentation describes what
each check does. `albums` can also help clean up and import new albums into your
library and keep digital audio players synced.

## Supported Media

**FLAC**, **Ogg Vorbis**, **MP3/ID3** and **M4A** containers are supported.
**WMA** files are read but `albums` doesn't comprehend their tags yet so most
checks are skipped. Image files (PNG, JPEG, GIF, BMP, WEBP, TIFF, etc) in the
album folder are scanned and can be automatically converted and embedded.

More formats and tag comprehension will likely be added if requested.

## System Requirements

Requires Python 3.12+. Primarily tested on Linux and Windows. Should work on
almost any 64-bit x86 or ARM system with Linux, macOS or Windows. (32-bit and
wider OS support possible by dropping `scikit-image` library used for measuring
image similarity.)
