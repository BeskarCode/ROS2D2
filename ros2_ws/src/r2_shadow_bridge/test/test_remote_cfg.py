# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""remote.yaml (the Remote window and the phone view) and the two rules the Mega bridge applies to
the virtual Navs: the stick limit and one owner at a time."""

import pytest

from r2_shadow_bridge.remote_cfg import (DEFAULTS, PadOwner, RemoteConfigError, limit_stick, load_remote,
                                         parse_remote)


def test_defaults_when_missing_or_broken(tmp_path):
    assert load_remote(str(tmp_path / "none.yaml")) == DEFAULTS
    p = tmp_path / "r.yaml"
    p.write_text("stick_limit_pct: [", encoding="utf-8")
    assert load_remote(str(p))["stick_limit_pct"] == 20
    p.write_text("stick_limit_pct: 500\n", encoding="utf-8")
    assert load_remote(str(p))["stick_limit_pct"] == 20       # never unlimited because of a bad file
    p.write_text("", encoding="utf-8")
    assert load_remote(str(p)) == DEFAULTS


def test_parse_checks_range_and_types():
    r = parse_remote("stick_limit_pct: 35\nguest: true\n")
    assert r["stick_limit_pct"] == 35 and r["guest"] is True and r["favorites"] == []
    for bad in ("stick_limit_pct: 500", "stick_limit_pct: 2", "stick_limit_pct: fast", "stick_limit_pct: true",
                "guest: maybe", "favorites: [{combo: NOPE, name: x}]", "favorites: [{combo: FOOT_UP, name: ''}]",
                "favorites: [{combo: FOOT_UP, name: 'a name far too long for a button'}]", "favorites: 3",
                "[1, 2]", "colour: red"):
        with pytest.raises(RemoteConfigError):
            parse_remote(bad)
    fav = parse_remote("favorites: [{combo: FOOT_UP, name: Scream}, {combo: DOME_PS_L2, name: Look}]")["favorites"]
    assert fav == [{"combo": "FOOT_UP", "name": "Scream"}, {"combo": "DOME_PS_L2", "name": "Look"}]


def test_limit_stick():
    assert limit_stick(255, 20) == 153 and limit_stick(0, 20) == 103      # L = round(127 * 0.2) = 25
    assert limit_stick(128, 20) == 128 and limit_stick(140, 20) == 140
    assert limit_stick(255, 100) == 255 and limit_stick(0, 100) == 1      # L = 127
    assert limit_stick(999, 20) == 153 and limit_stick(-5, 20) == 103
    assert limit_stick("200", 20) == 153 and limit_stick(None, 20) == 128  # junk = centred


def test_pad_owner():
    o = PadOwner(hold_s=1.0)
    assert o.owner is None
    assert o.accept("phone", 0.0) and not o.accept("pc", 0.5) and o.owner == "phone"
    assert o.accept("phone", 0.9)
    assert o.accept("pc", 2.0) and o.owner == "pc"      # the phone was quiet 1.1 s
    assert not o.accept("phone", 2.5)


def test_pad_owner_expires():
    o = PadOwner(hold_s=1.0)
    o.accept("phone", 0.0)
    assert o.expire(0.5) is False and o.owner == "phone"
    assert o.expire(1.2) is True and o.owner is None        # quiet > 1 s: nobody drives
    assert o.expire(1.3) is False                           # already free: no change to report
