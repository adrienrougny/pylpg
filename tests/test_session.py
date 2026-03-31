import pylpg.active_session


def test_active_session(session):
    active = pylpg.active_session.get_active_session()
    assert active is session


def test_no_active_session_raises():
    previous = pylpg.active_session.get_active_session_or_none()
    pylpg.active_session.set_active_session(None)
    try:
        pylpg.active_session.get_active_session()
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass
    finally:
        pylpg.active_session.set_active_session(previous)
