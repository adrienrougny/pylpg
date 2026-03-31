# pylpg

A Python Object Graph Mapper for labeled property graph databases.

## Features

- Simple model definition using Python type annotations
- Multi-backend: Neo4j, FalkorDB, FalkorDBLite (embedded)
- Implicit session management
- Node hydration from raw query results

## Installation

```bash
pip install pylpg[neo4j]        # Neo4j
pip install pylpg[falkordb]     # FalkorDB
pip install pylpg[falkordblite] # FalkorDBLite (embedded, no server)
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

backend = pylpg.backend.neo4j.Neo4jBackend(
    hostname="localhost",
    username="neo4j",
    password="password",
)

with pylpg.session.Session(backend) as session:
    alice = Person(name="Alice", age=30)
    bob = Person(name="Bob")
    alice.save()
    bob.save()

    rel = Knows(source=alice, target=bob, since="2024")
    rel.save()
```

## Documentation

Full documentation is available at [https://adienrougny.github.io/pylpg/](https://adrienrougny.github.io/pylpg/).

## License

GPLv3. See [LICENSE](LICENSE) for details.
