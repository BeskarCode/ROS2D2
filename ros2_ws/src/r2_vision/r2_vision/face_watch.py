# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""When the face detector needs the camera's pictures at all.

Its faces are only used with face tracking on (the dome follows them), with a mode on (Patrol
and Free roam greet people; any mode owns the dome) or with someone watching the picture with
the boxes (the web console). Otherwise it does not subscribe to image_raw, so the camera does
not publish 0.9 MB pictures 30 times a second for nobody."""


def wants_faces(track_on, mode, debug_watched):
    return bool(track_on) or bool(mode) or bool(debug_watched)


class FaceWatch:
    """The node's image_raw subscription as a small state machine (no ROS here, so it can be tested):
    update() says what to do now: "subscribe", "unsubscribe" or None (it already is as it should)."""

    def __init__(self):
        self.track_on, self.mode, self.subscribed = False, "", False

    def update(self, debug_watched, track_on=None, mode=None):
        if track_on is not None:
            self.track_on = bool(track_on)
        if mode is not None:
            self.mode = mode
        want = wants_faces(self.track_on, self.mode, debug_watched)
        if want == self.subscribed:
            return None
        self.subscribed = want
        return "subscribe" if want else "unsubscribe"
