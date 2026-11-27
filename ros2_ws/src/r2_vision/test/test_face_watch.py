# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_vision.face_watch import wants_faces


def test_pictures_only_when_someone_uses_the_faces():
    assert not wants_faces(False, "", False)             # tracking off, no mode, nobody watching (boot)
    assert wants_faces(True, "", False)                  # face tracking on
    assert wants_faces(False, "patrol", False)           # a mode on
    assert wants_faces(False, "", True)                  # the console shows faces/image
