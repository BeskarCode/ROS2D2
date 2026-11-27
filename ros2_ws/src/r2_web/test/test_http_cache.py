# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import os

from r2_web.http_cache import API, REVALIDATE, cache_control, etag


def test_api_never_kept_everything_else_revalidated():
    # REV-4: vendor/ and models/ too, so a new three.js or model reaches every browser at once
    assert cache_control("/api/cameras?detect=0") == API
    assert cache_control("/api/system") == API
    assert cache_control("/vendor/three.module.min.js") == REVALIDATE
    assert cache_control("/models/r2d2-vladimirov.glb") == REVALIDATE
    assert cache_control("/setup.js") == REVALIDATE
    assert cache_control("/") == REVALIDATE
    assert cache_control("/nav.html?x=1") == REVALIDATE


def test_etag_changes_with_the_content_even_with_an_older_time(tmp_path):
    f = tmp_path / "a.js"
    f.write_text("one", encoding="utf-8")
    first = etag(os.stat(f))
    assert first == etag(os.stat(f))
    f.write_text("two!", encoding="utf-8")
    os.utime(f, ns=(1, 1))                  # a deploy that leaves an old modification time
    assert etag(os.stat(f)) != first
