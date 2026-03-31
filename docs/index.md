# pylpg

**pylpg** is a Python Object Graph Mapper for labeled property graph databases. It maps Python classes to graph nodes and relationships, and generates queries for CRUD operations.

## Features

- **Simple model definition** — nodes and relationships are plain Python classes with type annotations
- **Multi-backend** — supports Neo4j, FalkorDB, and FalkorDBLite (embedded)
- **Batch operations** — optimized per backend (UNWIND for Neo4j, individual queries for FalkorDB)
- **Implicit session** — `node.save()` works without passing a session around
- **Node hydration** — raw query results can be automatically resolved into Python objects
- **Traversal** — relationship descriptors provide `all()` and `connect()` methods

## Installation

```bash
pip install pylpg
```

### Backend-specific extras

```bash
pip install pylpg[neo4j]        # Neo4j support
pip install pylpg[falkordb]     # FalkorDB support
pip install pylpg[falkordblite] # FalkorDBLite (embedded) support
pip install pylpg[all]          # All backends
```

## Quick example

```python
import pylpg.node
import pylpg.relationship
import pylpg.session
import pylpg.backend.neo4j

class Person(pylpg.node.Node):
    name: str
    age: int | None = None

class Knows(pylpg.relationship.Relationship):
    __type__ = "KNOWS"
    since: str | None = None

class PersonWithFriends(pylpg.node.Node):
    __labels__ = frozenset({"Person"})
    name: str
    friends = pylpg.relationship.RelationshipTo(Knows)

backend = pylpg.backend.neo4j.Neo4jBackend(
    hostname="localhost",
    username="neo4j",
    password="password",
)

with pylpg.session.Session(backend):
    alice = Person(name="Alice", age=30)
    bob = Person(name="Bob", age=25)

    # Save individually
    alice.save()
    bob.save()

    # Create relationship via connect()
    alice.friends.connect(bob, since="2024")

    # Or create relationship directly
    rel = Knows(source=alice, target=bob, since="2024")
    rel.save()

    # Batch save
    session.save([
        Person(name="Carol"),
        Person(name="Dave"),
    ])

    # Traverse
    friends = alice.friends.all()

    # Raw query with node hydration
    results = session.execute_query(
        "MATCH (n:Person) RETURN n",
        resolve_nodes=True,
    )
```

## Documentation

- [Getting started](getting_started.md) — detailed guide with examples
- [API reference](api_reference/node.md) — full API documentation
