import pytest

from r2_nav.modes import COMBOS, MODES, ModesConfigError, bindings, load_modes, parse_modes
import os


def test_combos_list():
    assert len(COMBOS) == 61 and len(set(COMBOS)) == 61
    assert COMBOS[0] == "FOOT_PS_L2" and COMBOS[1] == "FOOT_UP" and COMBOS[-1] == "DOME_RIGHT_L2_CIRCLE"
    assert "DOME_PS_L2" not in COMBOS


def test_defaults():
    cfg = parse_modes("")
    assert set(cfg) == set(MODES)
    assert cfg["goto"]["combo"] == "FOOT_PS_L2"
    assert cfg["follow"]["sound_on"] == "S1:$12" and cfg["follow"]["max_speed"] == 0.3
    assert cfg["follow"]["color"] is None and cfg["follow"]["camera"] == "cam1"
    assert bindings(cfg) == {"FOOT_PS_L2": "goto"}


def test_shipped_file_parses():
    here = os.path.dirname(__file__)
    cfg = load_modes(os.path.join(here, "..", "config", "modes.yaml"))
    assert bindings(cfg) == {"FOOT_PS_L2": "goto"}


def test_bad_combo():
    with pytest.raises(ModesConfigError, match="combo"):
        parse_modes("patrol: {combo: FOOT_BANANA}")


def test_duplicate_combo():
    with pytest.raises(ModesConfigError, match="combo"):
        parse_modes("forward: {combo: FOOT_UP}\npatrol: {combo: FOOT_UP}")
    with pytest.raises(ModesConfigError, match="combo"):
        parse_modes("forward: {combo: FOOT_PS_L2}")  # goto keeps its default


def test_dome_ps_l2_refused():
    with pytest.raises(ModesConfigError, match="DOME_PS_L2"):
        parse_modes("patrol: {combo: DOME_PS_L2}")


def test_follow_ranges():
    with pytest.raises(ModesConfigError, match="max_speed"):
        parse_modes("follow: {max_speed: 0.9}")
    with pytest.raises(ModesConfigError, match="hue_tol"):
        parse_modes("follow: {hue_tol: 1}")
    with pytest.raises(ModesConfigError, match="color"):
        parse_modes("follow: {color: {h: 200, s: 1, v: 1}}")
    assert parse_modes("follow: {color: {h: 100, s: 200, v: 90}}")["follow"]["color"] == {"h": 100, "s": 200, "v": 90}


def test_bad_sound_and_unknown_keys():
    with pytest.raises(ModesConfigError, match="sound_on"):
        parse_modes("follow: {sound_on: 'rm -rf'}")
    with pytest.raises(ModesConfigError, match="bogus"):
        parse_modes("bogus: {}")
    with pytest.raises(ModesConfigError, match="nope"):
        parse_modes("patrol: {nope: 1}")


def test_bindings_skip_null():
    cfg = parse_modes("goto: {combo: null}\nforward: {combo: DOME_UP_L1}")
    assert bindings(cfg) == {"DOME_UP_L1": "forward"}


def test_user_file_wins(tmp_path, monkeypatch):
    from r2_nav import modes
    user = tmp_path / "modes.yaml"
    monkeypatch.setattr(modes, "USER_MODES", str(user))
    assert modes.modes_path("/etc/x.yaml") == "/etc/x.yaml"
    user.write_text("")
    assert modes.modes_path("/etc/x.yaml") == str(user)


def test_nav_mode_the_navigator_runs():
    from r2_nav.modes import nav_mode
    assert nav_mode(None) == "goto"                 # an old bridge: as before
    assert [nav_mode(m) for m in ("goto", "forward", "patrol")] == ["goto", "forward", "patrol"]
    assert nav_mode("") == "goto"                   # off: the navigator still reports (manual)
    assert nav_mode("follow") is None
