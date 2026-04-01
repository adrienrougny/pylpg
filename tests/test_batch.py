import tests.models


def test_batch_create_nodes(session):
    nodes = [
        tests.models.Person(name="Alice"),
        tests.models.Person(name="Bob"),
        tests.models.Person(name="Carol"),
    ]
    session.save(nodes)
    for node in nodes:
        assert node.is_saved()


def test_batch_create_mixed_node_types(session):
    alice = tests.models.Person(name="Alice")
    cat = tests.models.Animal(species="Cat")
    session.save([alice, cat])
    assert alice.is_saved()
    assert cat.is_saved()


def test_batch_create_relationships(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    carol = tests.models.Person(name="Carol")
    relationships = [
        tests.models.Knows(source=alice, target=bob, since="2024"),
        tests.models.Knows(source=alice, target=carol, since="2023"),
    ]
    session.save(relationships)
    assert alice.is_saved()
    assert bob.is_saved()
    assert carol.is_saved()
    for relationship in relationships:
        assert relationship.is_saved()


def test_batch_update_nodes(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    session.save([alice, bob])
    alice.name = "Alice Updated"
    bob.name = "Bob Updated"
    session.save([alice, bob])
    assert alice.is_saved()
    assert bob.is_saved()


def test_batch_mixed_new_and_existing(session):
    alice = tests.models.Person(name="Alice")
    session.save(alice)
    bob = tests.models.Person(name="Bob")
    alice.name = "Alice Updated"
    session.save([alice, bob])
    assert alice.is_saved()
    assert bob.is_saved()


def test_batch_auto_collects_unsaved_nodes(session):
    alice = tests.models.Person(name="Alice")
    bob = tests.models.Person(name="Bob")
    relationship = tests.models.Knows(source=alice, target=bob)
    assert not alice.is_saved()
    assert not bob.is_saved()
    session.save([relationship])
    assert alice.is_saved()
    assert bob.is_saved()
    assert relationship.is_saved()
