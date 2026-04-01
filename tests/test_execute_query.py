import pylpg.node

import tests.models


def test_execute_query_raw(session):
    alice = tests.models.Person(name="Alice")
    session.save(alice)
    results = session.execute_query(
        "MATCH (node:Person {name: 'Alice'}) RETURN node.name AS name"
    )
    assert len(results) >= 1
    assert results[0]["name"] == "Alice"


def test_execute_query_with_resolve_nodes(session):
    alice = tests.models.Person(name="QueryResolve")
    session.save(alice)
    results = session.execute_query(
        "MATCH (node:Person {name: 'QueryResolve'}) RETURN node",
        resolve_nodes=True,
    )
    assert len(results) >= 1
    resolved_node = results[0]["node"]
    assert isinstance(resolved_node, tests.models.Person)
    assert resolved_node.name == "QueryResolve"


def test_execute_query_without_resolve_nodes(session):
    alice = tests.models.Person(name="QueryNoResolve")
    session.save(alice)
    results = session.execute_query(
        "MATCH (node:Person {name: 'QueryNoResolve'}) RETURN node",
        resolve_nodes=False,
    )
    assert len(results) >= 1
    raw_node = results[0]["node"]
    assert not isinstance(raw_node, pylpg.node.Node)


def test_execute_query_mixed_results(session):
    alice = tests.models.Person(name="MixedResult")
    session.save(alice)
    results = session.execute_query(
        "MATCH (node:Person {name: 'MixedResult'}) RETURN node, node.name AS name",
        resolve_nodes=True,
    )
    assert len(results) >= 1
    row = results[0]
    assert isinstance(row["node"], tests.models.Person)
    assert isinstance(row["name"], str)
    assert row["name"] == "MixedResult"
