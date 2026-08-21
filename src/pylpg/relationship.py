"""Relationship classes and descriptors for graph edges."""

import uuid
import typing
import enum

if typing.TYPE_CHECKING:
    import pylpg.session

import pylpg.types
import pylpg.node


class Relationship:
    """Base class for graph relationships.

    Subclass `Relationship` to define relationship types. The `__type__`
    class attribute is required and sets the relationship type in the database.

    Example:
        ```python
        class Knows(Relationship):
            __type__ = "KNOWS"
            since: str | None = None
        ```
    """

    __type__: str
    __primitive_properties__: typing.ClassVar[dict[str, typing.Any]]

    def __init_subclass__(cls, **kwargs: typing.Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "__type__") or not cls.__type__:
            raise ValueError(
                f"Relationship subclass '{cls.__name__}' must define __type__"
            )
        cls.__primitive_properties__ = pylpg.types.get_primitive_properties(cls)
        pylpg.types.validate_properties(cls.__primitive_properties__)

    def __init__(
        self,
        *,
        source: pylpg.node.Node,
        target: pylpg.node.Node,
        **kwargs: typing.Any,
    ) -> None:
        self._database_id = None
        self._temp_id = uuid.uuid4().hex
        self.source = source
        self.target = target
        for property_name in self.__primitive_properties__:
            if property_name in kwargs:
                setattr(self, property_name, kwargs[property_name])
            elif not hasattr(type(self), property_name):
                raise ValueError(f"Missing required property: {property_name}")

    def is_saved(self) -> bool:
        """Return True if this relationship has been saved to the database."""
        return self._database_id is not None

    def to_dict(self) -> dict[str, typing.Any]:
        """Return primitive properties as a dict, excluding None values."""
        result: dict[str, typing.Any] = {}
        for property_name in self.__primitive_properties__:
            property_value = getattr(self, property_name)
            if property_value is not None:
                result[property_name] = property_value
        return result


class Direction(enum.Enum):
    """Direction of a relationship traversal."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"
    UNDIRECTED = "either"


class BoundRelationship:
    """A relationship descriptor bound to a specific node instance.

    Provides `all()` to traverse and `connect()` to create relationships.
    """

    def __init__(
        self,
        owner: pylpg.node.Node,
        descriptor: "RelationshipDescriptor",
    ) -> None:
        self._owner = owner
        self._descriptor = descriptor

    def _get_session(self) -> "pylpg.session.Session":
        session = self._owner._session
        if session is None:
            raise ValueError(
                "Node is not bound to a session. Save it first with session.save()."
            )
        return session

    def all(self) -> list[pylpg.node.Node]:
        """Return all nodes connected to the owner via this relationship."""
        return [target for (target, _) in self._traverse()]

    def relationships(self) -> list[Relationship]:
        """Return the relationships connecting the owner to those nodes.

        Each relationship carries its properties, its source and its target.
        `all()` and `relationships()` are separate queries whose results are
        not necessarily in the same order, so they must not be paired up by
        position.

        Example:
            ```python
            for relationship in box.items.relationships():
                print(relationship.order, relationship.target)
            ```
        """
        relationship_class = self._descriptor._relationship_class
        relationships = []
        for target, deserialized_relationship in self._traverse():
            properties = {
                key: value
                for key, value in deserialized_relationship.items()
                if key in relationship_class.__primitive_properties__
            }
            if deserialized_relationship["_start_id"] == self._owner._database_id:
                (source, relationship_target) = (self._owner, target)
            else:
                (source, relationship_target) = (target, self._owner)
            relationship = relationship_class(
                source=source,
                target=relationship_target,
                **properties,
            )
            relationship._database_id = deserialized_relationship["_database_id"]
            relationships.append(relationship)
        return relationships

    def _traverse(self) -> list[tuple[pylpg.node.Node, dict[str, typing.Any]]]:
        return self._get_session()._traverse(
            node=self._owner,
            relationship_type=self._descriptor._relationship_class.__type__,
            direction=self._descriptor._direction,
        )

    def connect(self, target_node: pylpg.node.Node, **properties: typing.Any) -> None:
        """Create and save a relationship from the owner to target_node.

        Example:
            ```python
            session.save(alice)
            session.save(bob)
            alice.friends.connect(bob, since="2024")
            ```
        """
        session = self._get_session()
        if self._descriptor._direction == Direction.INCOMING:
            (source, target) = (target_node, self._owner)
        else:
            (source, target) = (self._owner, target_node)
        relationship = self._descriptor._relationship_class(
            source=source,
            target=target,
            **properties,
        )
        session.save(relationship)


class RelationshipDescriptor:
    """Descriptor that declares a relationship on a Node class.

    Use the convenience subclasses `RelationshipTo`, `RelationshipFrom`,
    and `RelationshipUndirected` instead of this class directly.
    """

    def __init__(
        self,
        direction: Direction,
        relationship_class: type[Relationship],
    ) -> None:
        self._direction = direction
        self._relationship_class = relationship_class

    def __get__(
        self, obj: pylpg.node.Node | None, type_: type | None = None
    ) -> "RelationshipDescriptor | BoundRelationship":
        if obj is None:
            return self
        return BoundRelationship(obj, self)


class RelationshipTo(RelationshipDescriptor):
    """Declares an outgoing relationship on a Node class.

    Example:
        ```python
        class Person(Node):
            name: str
            friends = RelationshipTo(Knows)
        ```
    """

    def __init__(
        self,
        relationship_class: type[Relationship],
    ) -> None:
        super().__init__(
            direction=Direction.OUTGOING,
            relationship_class=relationship_class,
        )


class RelationshipFrom(RelationshipDescriptor):
    """Declares an incoming relationship on a Node class.

    Example:
        ```python
        class Person(Node):
            name: str
            known_by = RelationshipFrom(Knows)
        ```
    """

    def __init__(
        self,
        relationship_class: type[Relationship],
    ) -> None:
        super().__init__(
            direction=Direction.INCOMING,
            relationship_class=relationship_class,
        )


class RelationshipUndirected(RelationshipDescriptor):
    """Declares an undirected relationship on a Node class.

    Example:
        ```python
        class Person(Node):
            name: str
            contacts = RelationshipUndirected(Knows)
        ```
    """

    def __init__(
        self,
        relationship_class: type[Relationship],
    ) -> None:
        super().__init__(
            direction=Direction.UNDIRECTED,
            relationship_class=relationship_class,
        )
