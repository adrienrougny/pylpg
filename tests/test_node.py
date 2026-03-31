import tests.models


def test_create_node(session):
    alice = tests.models.Person(name="Alice", age=30)
    assert not alice.is_saved()
    alice.save()
    assert alice.is_saved()
    assert alice._database_id is not None


def test_create_node_with_default(session):
    bob = tests.models.Person(name="Bob")
    bob.save()
    assert bob.is_saved()
    assert bob.age is None


def test_update_node(session):
    alice = tests.models.Person(name="Alice", age=30)
    alice.save()
    original_id = alice._database_id
    alice.name = "Alice Updated"
    alice.save()
    assert alice._database_id == original_id


def test_delete_node(session):
    alice = tests.models.Person(name="Alice")
    alice.save()
    assert alice.is_saved()
    alice.delete()
    assert not alice.is_saved()


def test_delete_unsaved_node_raises(session):
    alice = tests.models.Person(name="Alice")
    try:
        alice.delete()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_to_dict(session):
    alice = tests.models.Person(name="Alice", age=30)
    result = alice.to_dict()
    assert result == {"name": "Alice", "age": 30}


def test_to_dict_excludes_none(session):
    alice = tests.models.Person(name="Alice")
    result = alice.to_dict()
    assert result == {"name": "Alice"}
    assert "age" not in result


def test_missing_required_property_raises():
    try:
        tests.models.Person()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_node_labels():
    assert tests.models.Person.__labels__ == frozenset({"Person"})
    assert tests.models.Animal.__labels__ == frozenset({"Animal"})
