"""Node base class for mapping Python classes to graph nodes."""

import uuid
import typing

import pylpg.active_session
import pylpg.types


class Node:
    """Base class for graph nodes.

    Subclass `Node` to define graph node types. Properties are declared
    via type annotations, and labels default to the class name.

    Example:
        ```python
        class Person(Node):
            name: str
            age: int | None = None
        ```
    """

    __labels__: frozenset[str] = frozenset()
    __primitive_properties__: typing.ClassVar[dict[str, typing.Any]]
    __relationship_descriptors__: typing.ClassVar[dict[str, typing.Any]]
    __properties__: typing.ClassVar[dict[str, typing.Any]]

    _label_registry: typing.ClassVar[dict[frozenset[str], type["Node"]]] = {}
    _name_registry: typing.ClassVar[dict[str, type["Node"]]] = {}

    def __init_subclass__(cls, **kwargs: typing.Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.__labels__:
            cls.__labels__ = frozenset({cls.__name__})
        cls._label_registry[cls.__labels__] = cls
        cls._name_registry[cls.__name__] = cls
        cls.__primitive_properties__ = pylpg.types.get_primitive_properties(cls)
        pylpg.types.validate_properties(cls.__primitive_properties__)
        cls.__relationship_descriptors__ = pylpg.types.get_relationship_descriptors(cls)
        cls.__properties__ = {
            **cls.__primitive_properties__,
            **cls.__relationship_descriptors__,
        }

    def __init__(self, **kwargs: typing.Any) -> None:
        self._database_id = None
        self._temp_id = uuid.uuid4().hex
        for name in self.__primitive_properties__:
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif not hasattr(type(self), name):
                raise ValueError(f"Missing required property: {name}")

    @classmethod
    def resolve_class(cls, labels: frozenset[str]) -> type["Node"]:
        """Find the registered Node subclass with exactly the given labels."""
        node_class = cls._label_registry.get(labels)
        if node_class is None:
            raise ValueError(f"No registered Node class matches labels: {labels}")
        return node_class

    def is_saved(self) -> bool:
        """Return True if this node has been saved to the database."""
        return self._database_id is not None

    def to_dict(self) -> dict[str, typing.Any]:
        """Return primitive properties as a dict, excluding None values."""
        result: dict[str, typing.Any] = {}
        for property_name in self.__primitive_properties__:
            value = getattr(self, property_name)
            if value is not None:
                result[property_name] = value
        return result

    def save(self) -> None:
        """Save this node to the database using the active session."""
        pylpg.active_session.get_active_session().save(self)

    def delete(self) -> None:
        """Delete this node from the database using the active session."""
        pylpg.active_session.get_active_session().delete(self)
