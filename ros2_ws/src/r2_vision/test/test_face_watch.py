# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_vision.face_watch import wants_faces


def test_pictures_only_when_someone_uses_the_faces():
    assert not wants_faces(False, "", False)             # tracking off, no mode, nobody watching (boot)
    assert wants_faces(True, "", False)                  # face tracking on
    assert wants_faces(False, "patrol", False)           # a mode on
    assert wants_faces(False, "", True)                  # the console shows faces/image


def test_subscribe_and_unsubscribe_only_on_a_change():
    # REV-T8: what the node does with image_raw as tracking, the mode and the console come and go
    from r2_vision.face_watch import FaceWatch
    w = FaceWatch()
    assert w.update(False) is None                                  # boot: nothing in use, nothing to do
    assert w.update(False, track_on=True) == "subscribe"           # face tracking on
    assert w.update(False) is None                                  # the 1 s timer: no change
    assert w.update(False, mode="patrol") is None                   # still wanted (two reasons now)
    assert w.update(False, track_on=False) is None                  # the mode keeps it
    assert w.update(False, mode="") == "unsubscribe"                # nothing left: camera alone
    assert w.update(True) == "subscribe"                            # the console opens faces/image
    assert w.update(False) == "unsubscribe"                         # and closes it
