from app.imaging import PreparedImage
from app.sessions import SessionStore


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def _image():
    return PreparedImage(data=b"x", mime_type="image/jpeg", width=1, height=1, original_bytes=1)


def test_create_and_get():
    store = SessionStore()
    s = store.create()
    assert store.get(s.id) is s
    assert store.get("nope") is None


def test_sessions_expire_after_the_ttl():
    clock = Clock()
    store = SessionStore(ttl_seconds=100, clock=clock)
    s = store.create()
    clock.now = 101.0
    assert store.get(s.id) is None


def test_using_a_session_keeps_it_alive():
    clock = Clock()
    store = SessionStore(ttl_seconds=100, clock=clock)
    s = store.create()
    clock.now = 60.0
    assert store.get(s.id) is s
    clock.now = 120.0
    assert store.get(s.id) is s


def test_oldest_session_is_evicted_when_full():
    clock = Clock()
    store = SessionStore(max_sessions=2, clock=clock)
    a = store.create()
    clock.now = 1.0
    b = store.create()
    clock.now = 2.0
    c = store.create()
    assert store.get(a.id) is None
    assert store.get(b.id) is b
    assert store.get(c.id) is c


def test_history_is_trimmed_to_max_turns():
    store = SessionStore(max_turns=2)
    s = store.create()
    for i in range(5):
        store.add_turn(s, f"q{i}", f"a{i}")
    assert [turn.text for turn in s.history] == ["q3", "a3", "q4", "a4"]


def test_new_image_clears_the_history():
    store = SessionStore()
    s = store.create()
    store.add_turn(s, "q", "a")
    store.set_image(s, _image())
    assert s.history == []
    assert s.image is not None


def test_delete():
    store = SessionStore()
    s = store.create()
    assert store.delete(s.id) is True
    assert store.delete(s.id) is False
