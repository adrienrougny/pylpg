import pylpg.node
import pylpg.relationship


class Person(pylpg.node.Node):
    name: str
    age: int | None = None


class Animal(pylpg.node.Node):
    species: str


class Knows(pylpg.relationship.Relationship):
    __type__ = "KNOWS"
    since: str | None = None


class Owns(pylpg.relationship.Relationship):
    __type__ = "OWNS"


class Person2(pylpg.node.Node):
    """Person with relationship descriptors for traversal tests."""

    __labels__ = frozenset({"Person2"})
    name: str
    friends = pylpg.relationship.RelationshipTo(
        relationship_class=Knows,
    )
    known_by = pylpg.relationship.RelationshipFrom(
        relationship_class=Knows,
    )
