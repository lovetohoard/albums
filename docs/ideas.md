---
icon: lucide/flask-conical
---

# Ideas

## General features

- Select/filter albums based on track tags, stream info, recent access, etc
- Support additional file formats
- Faster scan (only update what changed, don't decompress images again)
- Localize interface
- Improve Unicode support (if there are problems?)
- Option to use ID3 2.3 instead of 2.4 if people still do that

### More checks and fixes

- many suggested fixes for current no-fix check failures in TODOs
- low bitrate or suboptimal codec
- not all tracks encoded the same (file type or kbps target)
- track filename doesn't match title, doesn't include track/disc number
- album folder doesn't match album name
- parent folder doesn't match artist if using artist/album
- automatic visual similarity check for front cover art, so it can be stored in
  multiple formats and resolutions without disabling uniqueness check
