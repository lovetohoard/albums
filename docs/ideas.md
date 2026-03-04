---
icon: lucide/flask-conical
---

# Ideas

## General features

- Select/filter albums based on track tags, recent access, other
- Configure what to do when encountering various ID3 versions
- Support additional file formats

### More checks and fixes

- low bitrate or suboptimal codec
- not all tracks encoded the same (file type or kbps target)
- track filename doesn't match title, doesn't include track/disc number
- album folder doesn't match album name
- parent folder doesn't match artist if using artist/album
- automatic visual similarity check for front cover art, so it can be stored in
  multiple formats and resolutions without disabling uniqueness check
