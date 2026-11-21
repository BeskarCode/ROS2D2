# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# python -m pytest setup/test
import importlib.machinery
import importlib.util
import os

HERE = os.path.dirname(__file__)
_loader = importlib.machinery.SourceFileLoader("r2_wifi_channel", os.path.join(HERE, "..", "r2-wifi-channel"))
_spec = importlib.util.spec_from_loader("r2_wifi_channel", _loader)
w = importlib.util.module_from_spec(_spec)
_loader.exec_module(w)

SCAN = """BSS 9c:53:22:0b:e0:8e(on wlan0)
\tfreq: 2432
\tsignal: -38.00 dBm
\tSSID: wifi
BSS a2:53:22:0b:e0:e6(on wlan0)
\tfreq: 2432.0
\tsignal: -45.00 dBm
\tSSID: wifiguest
BSS 9c:53:22:0b:e0:8f(on wlan0)
\tfreq: 5180
\tsignal: -40.00 dBm
\tSSID: wifi
BSS cc:ed:dc:64:fd:86(on wlan0)
\tfreq: 2462
\tsignal: -80.00 dBm
\tSSID: MOVISTAR_FD84
BSS 1c:e8:9e:c7:e3:1b(on wlan0)
\tfreq: 2412
\tsignal: -50.00 dBm
\tSSID: Samsung Fridge
"""


def test_parse_keeps_only_2_4_ghz():
    nets = w.parse_scan(SCAN)
    assert [(n["ssid"], n["channel"], n["dbm"]) for n in nets] == [
        ("wifi", 5, -38.0), ("wifiguest", 5, -45.0), ("MOVISTAR_FD84", 11, -80.0), ("Samsung Fridge", 1, -50.0)]


def test_the_home_mesh_on_5_rules_out_6_and_the_weak_neighbour_on_11_wins():
    # today's case: a strong mesh on 5 (overlaps 6 almost fully, and 1 a little), a fridge on 1
    sc = w.scores(w.parse_scan(SCAN))
    assert w.best(sc) == 11
    assert sc[6] > sc[1] > sc[11]


def test_own_ap_and_far_channels_do_not_count():
    nets = [{"ssid": "R2D2", "channel": 6, "dbm": -20.0}, {"ssid": "x", "channel": 1, "dbm": -60.0}]
    sc = w.scores(nets, own_ssid="R2D2")
    assert sc[6] == 0 and sc[11] == 0 and sc[1] > 0
    assert w.best(sc) == 6           # a tie between 6 and 11: the lower one


def test_nothing_around_keeps_1():
    assert w.best(w.scores([])) == 1


def test_conf_channel_is_replaced_or_added():
    conf = "interface=wlan0\nssid=R2D2\nchannel=6\nieee80211n=1\n"
    assert w.current(conf) == 6 and w.own_ssid(conf) == "R2D2"
    assert "channel=11\n" in w.set_channel(conf, 11) and "channel=6" not in w.set_channel(conf, 11)
    assert w.set_channel("ssid=R2D2\n", 1).endswith("channel=1\n")


def test_channel_of():
    assert w.channel_of(2412) == 1 and w.channel_of(2437) == 6 and w.channel_of(2462) == 11
    assert w.channel_of(2484) == 14 and w.channel_of(5180) is None
