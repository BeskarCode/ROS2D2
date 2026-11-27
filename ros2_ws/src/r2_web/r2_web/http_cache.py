# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""How long the browser may keep what the web console serves.

/api/ answers: never kept. Everything else (the pages, their modules, vendor/ with three.js and
the icon font, models/ with the R2 model): kept, but asked again every time; the server answers
304 when the file has not changed (its ETag), so the ~1 MB of three.js and the model is not
downloaded again on every page change, and an update (a new three.js, a new model) reaches every
browser at once. vendor/ is not kept for a week without asking: its files load each other (the
loaders, the font files) by paths that carry no version, so a ?v= could not reach them all."""

API = "no-store"
REVALIDATE = "no-cache"


def cache_control(path):
    return API if path.split("?")[0].startswith("/api/") else REVALIDATE


def etag(st):
    """A tag that changes with the file's size or modification time (to the nanosecond): a deploy
    that leaves an older modification time still changes it (Last-Modified alone would not)."""
    return f'"{st.st_size:x}-{st.st_mtime_ns:x}"'
