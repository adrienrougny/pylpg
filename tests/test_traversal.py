import contextlib

import pytest

import pylpg.relationship

import tests.models


@contextlib.contextmanager
def count_queries(backend):
    """Count backend queries issued inside the block."""
    counter = {"count": 0}
    original_execute_query = backend.execute_query

    def counting_execute_query(cypher, parameters=None):
        counter["count"] += 1
        return original_execute_query(cypher, parameters)

    backend.execute_query = counting_execute_query
    try:
        yield counter
    finally:
        del backend.execute_query


@pytest.fixture
def diamond(session):
    """A diamond (root -> left/right -> sink), plus a leaf with no edges.

    Returns the root and the leaf.
    """
    root = tests.models.Person2(name="Root")
    left = tests.models.Person2(name="Left")
    right = tests.models.Person2(name="Right")
    sink = tests.models.Person2(name="Sink")
    leaf = tests.models.Person2(name="Leaf")
    session.save([root, left, right, sink, leaf])
    root.friends.connect(left)
    root.friends.connect(right)
    left.friends.connect(sink)
    right.friends.connect(sink)
    return root, leaf


def test_traverse_outgoing(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    session.save(alice)
    session.save(bob)
    alice.friends.connect(bob)
    friends = alice.friends.all()
    assert len(friends) == 1
    assert friends[0].name == "Bob"


def test_traverse_incoming(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    session.save(alice)
    session.save(bob)
    alice.friends.connect(bob)
    known_by = bob.known_by.all()
    assert len(known_by) == 1
    assert known_by[0].name == "Alice"


def test_traverse_returns_correct_type(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    session.save(alice)
    session.save(bob)
    alice.friends.connect(bob)
    friends = alice.friends.all()
    assert isinstance(friends[0], tests.models.Person2)


def test_traverse_empty(session):
    alice = tests.models.Person2(name="Alice")
    session.save(alice)
    friends = alice.friends.all()
    assert friends == []


def test_traverse_multiple(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    carol = tests.models.Person2(name="Carol")
    session.save(alice)
    session.save(bob)
    session.save(carol)
    alice.friends.connect(bob)
    alice.friends.connect(carol)
    friends = alice.friends.all()
    assert len(friends) == 2
    names = {friend.name for friend in friends}
    assert names == {"Bob", "Carol"}


def test_connect_with_properties(session):
    alice = tests.models.Person2(name="Alice")
    bob = tests.models.Person2(name="Bob")
    session.save(alice)
    session.save(bob)
    alice.friends.connect(bob, since="2024")
    friends = alice.friends.all()
    assert len(friends) == 1


def test_traverse_unsaved_node_raises():
    alice = tests.models.Person2(name="Alice")
    try:
        alice.friends.all()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def _ids(nodes):
    """Node defines no __eq__, so compare database ids, not instances."""
    return sorted(str(node._database_id) for node in nodes)


def _traverse_diamond(root, leaf):
    root.known_by.all()
    leaf.friends.all()
    leaf.known_by.all()
    for child in root.friends.all():
        child.known_by.all()
        for grandchild in child.friends.all():
            grandchild.friends.all()
            grandchild.known_by.all()


def test_prefetch_matches_live_traversal(session, diamond):
    (root, leaf) = diamond
    live_friends = _ids(root.friends.all())
    live_known_by = _ids(root.known_by.all())
    live_leaf = _ids(leaf.friends.all())
    live_children = {
        str(child._database_id): _ids(child.friends.all())
        for child in root.friends.all()
    }
    with session.prefetch(roots=[root, leaf]):
        assert _ids(root.friends.all()) == live_friends
        assert _ids(root.known_by.all()) == live_known_by
        assert _ids(leaf.friends.all()) == live_leaf
        assert {
            str(child._database_id): _ids(child.friends.all())
            for child in root.friends.all()
        } == live_children


def test_prefetch_duplicate_roots_do_not_duplicate_children(session, diamond):
    (root, _) = diamond
    live_friends = _ids(root.friends.all())
    duplicate = tests.models.Person2(name=root.name)
    duplicate._database_id = root._database_id
    duplicate._session = session
    with session.prefetch(roots=[root, duplicate]):
        assert _ids(root.friends.all()) == live_friends
        assert _ids(duplicate.friends.all()) == live_friends


def test_prefetch_traversal_issues_no_queries(session, backend, diamond):
    (root, leaf) = diamond
    with session.prefetch(roots=[root, leaf]):
        with count_queries(backend) as counter:
            _traverse_diamond(root, leaf)
    assert counter["count"] == 0


def test_prefetch_reduces_query_count(session, backend, diamond):
    (root, leaf) = diamond
    with count_queries(backend) as live_counter:
        _traverse_diamond(root, leaf)
    with count_queries(backend) as prefetch_counter:
        with session.prefetch(roots=[root, leaf]):
            _traverse_diamond(root, leaf)
    # One (relationship type, direction) key per level: KNOWS outgoing and
    # KNOWS incoming, over three levels (roots, children, grandchildren).
    assert prefetch_counter["count"] <= 6
    assert prefetch_counter["count"] < live_counter["count"]


@contextlib.contextmanager
def force_result_set_limit(backend, limit):
    """Pretend the backend truncates result sets at `limit` rows.

    Also truncates real result sets, so a batch that is not split loses rows
    exactly as FalkorDB's RESULTSET_SIZE would.
    """
    original_traverse_batch_chunk = backend._traverse_batch_chunk

    def truncating_traverse_batch_chunk(source_ids, relationship_type, direction):
        rows = original_traverse_batch_chunk(
            source_ids=source_ids,
            relationship_type=relationship_type,
            direction=direction,
        )
        return rows[:limit]

    backend.result_set_limit = lambda: limit
    backend._traverse_batch_chunk = truncating_traverse_batch_chunk
    try:
        yield
    finally:
        del backend.result_set_limit
        del backend._traverse_batch_chunk


def test_prefetch_splits_batches_at_result_set_limit(session, backend):
    # Three roots with one child each: no single node exceeds a limit of 2,
    # but the three of them batched together return 3 rows, so traverse_batch
    # must split the batch rather than lose the third row. The diamond fixture
    # cannot be reused: its root has 2 children, so any limit low enough to
    # force a split also makes the root unsplittable.
    roots = [tests.models.Person2(name=f"Root{index}") for index in range(3)]
    children = [tests.models.Person2(name=f"Child{index}") for index in range(3)]
    session.save(roots + children)
    for root, child in zip(roots, children):
        root.friends.connect(child)
    live = {str(root._database_id): _ids(root.friends.all()) for root in roots}
    with force_result_set_limit(backend, limit=2):
        with session.prefetch(roots=roots):
            assert {
                str(root._database_id): _ids(root.friends.all()) for root in roots
            } == live


def test_traverse_batch_raises_when_single_node_exceeds_limit(
    session, backend, diamond
):
    (root, _) = diamond
    with force_result_set_limit(backend, limit=1):
        with pytest.raises(ValueError, match="result set limit"):
            backend.traverse_batch(
                source_ids=[root._database_id],
                relationship_type="KNOWS",
                direction=pylpg.relationship.Direction.OUTGOING,
            )


def test_traversal_after_prefetch_queries_live(session, backend, diamond):
    (root, _) = diamond
    with session.prefetch(roots=[root]):
        pass
    with count_queries(backend) as counter:
        root.friends.all()
    assert counter["count"] == 1


def test_relationships_read_properties(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=3)
    relationships = box.items.relationships()
    assert len(relationships) == 1
    assert relationships[0].order == 3
    assert relationships[0].source._database_id == box._database_id
    assert relationships[0].target._database_id == item._database_id


def test_relationships_without_properties(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item)
    relationships = box.items.relationships()
    assert len(relationships) == 1
    assert relationships[0].order is None


def test_relationships_incoming(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=1)
    relationships = item.items_of.relationships()
    assert len(relationships) == 1
    assert relationships[0].order == 1
    assert relationships[0].source._database_id == box._database_id
    assert relationships[0].target._database_id == item._database_id


def test_relationships_undirected_keeps_stored_direction(session):
    left = tests.models.Person3(name="Left")
    middle = tests.models.Person3(name="Middle")
    right = tests.models.Person3(name="Right")
    session.save([left, middle, right])
    middle.items.connect(right, order=1)
    left.items.connect(middle, order=2)
    relationships = middle.linked.relationships()
    by_order = {relationship.order: relationship for relationship in relationships}
    assert set(by_order) == {1, 2}
    assert by_order[1].source._database_id == middle._database_id
    assert by_order[1].target._database_id == right._database_id
    assert by_order[2].source._database_id == left._database_id
    assert by_order[2].target._database_id == middle._database_id


def test_relationships_parallel_edges(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=0)
    box.items.connect(item, order=1)
    relationships = box.items.relationships()
    assert sorted(relationship.order for relationship in relationships) == [0, 1]
    assert len(box.items.all()) == 2


def test_relationships_self_loop(session):
    person = tests.models.Person3(name="Loop")
    session.save(person)
    person.items.connect(person, order=7)
    for bound_relationship in (person.items, person.items_of, person.linked):
        relationships = bound_relationship.relationships()
        assert len(relationships) == 1
        assert relationships[0].order == 7
        assert relationships[0].source._database_id == person._database_id
        assert relationships[0].target._database_id == person._database_id


def test_relationships_rebuild_ordered_list(session):
    box = tests.models.Person3(name="Box")
    items = [tests.models.Person3(name=name) for name in ("z", "y", "x")]
    shared = tests.models.Person3(name="q")
    session.save([shared, box, *items])
    for index, item in enumerate([*items, shared]):
        box.items.connect(item, order=index)
    relationships = sorted(
        box.items.relationships(), key=lambda relationship: relationship.order
    )
    names = [relationship.target.name for relationship in relationships]
    assert names == ["z", "y", "x", "q"]


def test_relationships_match_prefetch(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=4)
    live = box.items.relationships()
    with session.prefetch(roots=[box]):
        prefetched = box.items.relationships()
    assert [relationship.order for relationship in live] == [
        relationship.order for relationship in prefetched
    ]
    assert [relationship._database_id for relationship in live] == [
        relationship._database_id for relationship in prefetched
    ]


def test_relationships_issue_no_queries_after_prefetch(session, backend):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=5)
    with session.prefetch(roots=[box]):
        with count_queries(backend) as counter:
            box.items.relationships()
    assert counter["count"] == 0


def test_relationship_from_traversal_updates_instead_of_creating(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=1)
    relationship = box.items.relationships()[0]
    assert relationship.is_saved()
    relationship.order = 2
    session.save(relationship)
    relationships = box.items.relationships()
    assert len(relationships) == 1
    assert relationships[0].order == 2


def test_all_returns_nodes(session):
    box = tests.models.Person3(name="Box")
    item = tests.models.Person3(name="Item")
    session.save([box, item])
    box.items.connect(item, order=1)
    (found,) = box.items.all()
    assert isinstance(found, tests.models.Person3)
    assert found.name == "Item"
