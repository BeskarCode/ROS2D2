# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""How long the browser may keep what the web console serves.

/api/ answers: never kept. vendor/ (three.js, its loaders, the icon font) and models/ (the R2
model): kept a week; they only change when three.js is updated (then a ?v= in the importmap).
Everything else (the pages and their modules): kept, but asked again every time; the server
answers 304 when the file has not changed, so the ~1 MB of three.js and the model is not
downloaded again on every page change."""

API = "no-store"
LONG = "public, max-age=604800"
REVALIDATE = "no-cache"


def cache_control(path):
    p = path.split("?")[0]
    if p.startswith("/api/"):
        return API
    if p.startswith(("/vendor/", "/models/")):
        return LONG
    return REVALIDATE


def etag(st):
    """A tag that changes with the file's size or modification time (to the nanosecond): a deploy
    that leaves an older modification time still changes it (Last-Modified alone would not)."""
    return f'"{st.st_size:x}-{st.st_mtime_ns:x}"'
