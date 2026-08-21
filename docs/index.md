# pylpg

**pylpg** is a Python Object Graph Mapper for labeled property graph databases. It maps Python classes to graph nodes and relationships, and generates queries for CRUD operations.

## Features

- **Simple model definition** — nodes and relationships are plain Python classes with type annotations
- **Multi-backend** — supports Neo4j, FalkorDB, and FalkorDBLite (embedded)
- **Batch operations** — optimized per backend (UNWIND for Neo4j, individual queries for FalkorDB)
- **Session-based persistence** — saved nodes are bound to their session for traversal and updates
- **Node hydration** — raw query results can be automatically resolved into Python objects
- **Traversal** — relationship descriptors provide `all()`, `relationships()` and `connect()` methods

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

with pylpg.session.Session(backend) as session:
    alice = Person(name="Alice", age=30)
    bob = Person(name="Bob", age=25)

    # Save individually
    session.save(alice)
    session.save(bob)

    # Create relationship via connect() (node must be saved first)
    alice.friends.connect(bob, since="2024")

    # Or create relationship directly
    rel = Knows(source=alice, target=bob, since="2024")
    session.save(rel)

    # Batch save
    session.save([
        Person(name="Carol"),
        Person(name="Dave"),
    ])

    # Traverse (node is bound to session after save)
    friends = alice.friends.all()

    # Traverse and read the properties on the relationships
    for relationship in alice.friends.relationships():
        print(relationship.target.name, relationship.since)

    # Raw query with node hydration
    results = session.execute_query(
        "MATCH (n:Person) RETURN n",
        resolve_nodes=True,
    )
```

## Documentation

- [Getting started](getting_started.md) — detailed guide with examples
- [API reference](api_reference/node.md) — full API documentation
