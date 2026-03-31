import tests.models


def test_traverse_outgoing(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    alice.save()
    bob.save()
    alice.friends.connect(bob)
    friends = alice.friends.all()
    assert len(friends) == 1
    assert friends[0].name == "Bob"


def test_traverse_incoming(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    alice.save()
    bob.save()
    alice.friends.connect(bob)
    known_by = bob.known_by.all()
    assert len(known_by) == 1
    assert known_by[0].name == "Alice"


def test_traverse_returns_correct_type(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    alice.save()
    bob.save()
    alice.friends.connect(bob)
    friends = alice.friends.all()
    assert isinstance(friends[0], tests.models.Person2)


def test_traverse_empty(session):
    alice = tests.models.Person2(name="Alice")
    alice.save()
    friends = alice.friends.all()
    assert friends == []


def test_traverse_multiple(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    carol = tests.models.Person2(name="Carol")
    alice.save()
    bob.save()
    carol.save()
    alice.friends.connect(bob)
    alice.friends.connect(carol)
    friends = alice.friends.all()
    assert len(friends) == 2
    names = {friend.name for friend in friends}
    assert names == {"Bob", "Carol"}


def test_connect_with_properties(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    alice.save()
    bob.save()
    alice.friends.connect(bob, since="2024")
    friends = alice.friends.all()
    assert len(friends) == 1
