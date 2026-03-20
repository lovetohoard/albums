---
icon: lucide/wrench
---

# Technical Notes

## Tag Conversion

`albums` attempts to apply some of the same checks and rules with Vorbis
comments (FLAC, Ogg Vorbis), ID3 tags (MP3) and MP4 iTunes atoms (M4A). To
enable this, common tags like track number are converted to the typical Vorbis
comment tag names. For example, the ID3 tags TPE1 "Artist" and TPE2 "Band" are
referenced by the standard tag names "artist" and "albumartist". Or in other
words, if `albums` writes a new "album artist" to your MP3, behind the scenes
it's actually writing to the TPE2 tag.

### Track total and disc total

If track number and track total are combined in the tracknumber (or ID3 TRCK)
with a slash like "04/12" instead of being in separate tags, `albums` will see
that as "tracknumber=04" and "tracktotal=12" and be able to write to the track
number and track total field as if they were separate. The same rule applies for
disc number and disc total if combined in the discnumber (or ID3 TPOS) tag.
Storing track total and disc total this way is normal for ID3 tags.
