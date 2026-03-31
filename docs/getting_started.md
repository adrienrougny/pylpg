# Getting started

## Defining models

### Nodes

Subclass `Node` and declare properties as type annotations:

```python
import pylpg.node

class Person(pylpg.node.Node):
    name: str
    age: int | None = None
```

Labels default to the class name. To set custom labels:

```python
class Employee(pylpg.node.Node):
    __labels__ = frozenset({"Person", "Employee"})
    name: str
    role: str
```

### Relationships

Subclass `Relationship` with a `__type__` attribute:

```python
import pylpg.relationship

class Knows(pylpg.relationship.Relationship):
    __type__ = "KNOWS"
    since: str | None = None
```

### Relationship descriptors

Attach traversal capabilities to nodes using descriptors:

```python
class Person(pylpg.node.Node):
    name: str
    friends = pylpg.relationship.RelationshipTo(Knows)
    known_by = pylpg.relationship.RelationshipFrom(Knows)
```

Available descriptors:

- `RelationshipTo` — outgoing relationships
- `RelationshipFrom` — incoming relationships
- `RelationshipUndirected` — undirected relationships

## Connecting to a database

### Neo4j

```python
import pylpg.backend.neo4j

backend = pylpg.backend.neo4j.Neo4jBackend(
    hostname="localhost",
    port=7687,
    database="neo4j",
    username="neo4j",
    password="password",
    protocol="bolt",
)
```

### FalkorDB

```python
import pylpg.backend.falkordb

backend = pylpg.backend.falkordb.FalkorDBBackend(
    hostname="localhost",
    port=6379,
    database="default",
)
```

### FalkorDBLite (embedded)

No server required:

```python
import pylpg.backend.falkordblite

backend = pylpg.backend.falkordblite.FalkorDBLiteBackend(
    path="/tmp/my_graph.db",
    database="default",
)
```

## Sessions

A session manages the connection between your Python objects and the database. Use it as a context manager:

```python
import pylpg.session

with pylpg.session.Session(backend) as session:
    alice = Person(name="Alice")
    alice.save()
```

Within the `with` block, `node.save()` and `node.delete()` use the active session automatically.

## CRUD operations

### Creating nodes

```python
alice = Person(name="Alice", age=30)
alice.save()
```

### Updating nodes

```python
alice.name = "Alice Smith"
alice.save()
```

### Deleting nodes

```python
alice.delete()
```

### Creating relationships

Two approaches:

**Direct instantiation:**

```python
rel = Knows(source=alice, target=bob, since="2024")
rel.save()  # auto-saves unsaved source/target nodes
```

**Via descriptor:**

```python
alice.friends.connect(bob, since="2024")
```

### Traversal

```python
friends = alice.friends.all()
for friend in friends:
    print(friend.name)
```

## Batch operations

Save multiple items at once using `session.save(list)`:

```python
nodes = [Person(name=f"person_{i}") for i in range(1000)]
session.save(nodes)
```

Batch save also works with relationships and automatically saves unsaved referenced nodes:

```python
relationships = [
    Knows(source=alice, target=bob),
    Knows(source=alice, target=carol),
]
session.save(relationships)
```

Each backend implements batch operations optimally:

- **Neo4j** — uses `UNWIND` queries for massive speedups (up to 40x at 50k items)
- **FalkorDB / FalkorDBLite** — uses individual queries (optimal for these backends)

## Raw queries

Execute Cypher queries directly:

```python
results = session.execute_query(
    "MATCH (n:Person) WHERE n.age > $min_age RETURN n",
    parameters={"min_age": 25},
)
```

Use `resolve_nodes=True` to automatically hydrate driver node objects into Python instances:

```python
results = session.execute_query(
    "MATCH (n:Person) RETURN n",
    resolve_nodes=True,
)
for row in results:
    person = row["n"]  # a Person instance
    print(person.name)
```

## Property types

Allowed property types are:

- Primitives: `str`, `int`, `float`, `bool`, `None`
- Lists of primitives: `list[str]`, `list[int]`, etc.
- Unions of the above: `str | None`, `int | float`, etc.

Properties with default values are optional. Properties without defaults are required:

```python
class Person(pylpg.node.Node):
    name: str                    # required
    age: int | None = None       # optional, defaults to None
    score: float = 0.0           # optional, defaults to 0.0
```
