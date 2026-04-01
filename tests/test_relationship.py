import tests.models


def test_create_relationship(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    rel = tests.models.Knows(source=alice, target=bob, since="2024")
    assert not rel.is_saved()
    session.save(rel)
    assert rel.is_saved()
    assert alice.is_saved()
    assert bob.is_saved()


def test_create_relationship_auto_saves_nodes(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    assert not alice.is_saved()
    assert not bob.is_saved()
    rel = tests.models.Knows(source=alice, target=bob)
    session.save(rel)
    assert alice.is_saved()
    assert bob.is_saved()


def test_update_relationship(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    rel = tests.models.Knows(source=alice, target=bob, since="2024")
    session.save(rel)
    original_id = rel._database_id
    rel.since = "2025"
    session.save(rel)
    assert rel._database_id == original_id


def test_delete_relationship(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    rel = tests.models.Knows(source=alice, target=bob)
    session.save(rel)
    assert rel.is_saved()
    session.delete(rel)
    assert not rel.is_saved()


def test_delete_unsaved_relationship_raises(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    rel = tests.models.Knows(source=alice, target=bob)
    try:
        session.delete(rel)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_relationship_to_dict(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    rel = tests.models.Knows(source=alice, target=bob, since="2024")
    assert rel.to_dict() == {"since": "2024"}


def test_relationship_to_dict_excludes_none(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    rel = tests.models.Knows(source=alice, target=bob)
    assert rel.to_dict() == {}
