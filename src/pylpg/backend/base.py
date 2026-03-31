"""Abstract base class for database backends."""

import abc
import typing

if typing.TYPE_CHECKING:
    import pylpg.node
    import pylpg.relationship


class Backend(abc.ABC):
    """Abstract base class that all database backends must implement.

    Backends handle all direct database operations: CRUD for nodes and
    relationships, batch operations, traversal, and query execution.
    """

    @abc.abstractmethod
    def execute_query(
        self, cypher: str, parameters: dict[str, typing.Any] | None = None
    ) -> list[dict[str, typing.Any]]: ...

    @abc.abstractmethod
    def is_node(self, value: typing.Any) -> bool: ...

    @abc.abstractmethod
    def deserialize_node(self, record: typing.Any) -> dict[str, typing.Any]: ...

    @abc.abstractmethod
    def create_node(self, node: "pylpg.node.Node") -> dict[str, typing.Any]: ...

    @abc.abstractmethod
    def update_node(self, node: "pylpg.node.Node") -> dict[str, typing.Any]: ...

    @abc.abstractmethod
    def delete_node(self, node: "pylpg.node.Node") -> None: ...

    @abc.abstractmethod
    def create_relationship(
        self, relationship: "pylpg.relationship.Relationship"
    ) -> dict[str, typing.Any]: ...

    @abc.abstractmethod
    def update_relationship(
        self, relationship: "pylpg.relationship.Relationship"
    ) -> dict[str, typing.Any]: ...

    @abc.abstractmethod
    def delete_relationship(
        self, relationship: "pylpg.relationship.Relationship"
    ) -> None: ...

    @abc.abstractmethod
    def save_batch(
        self,
        items: "list[pylpg.node.Node | pylpg.relationship.Relationship]",
    ) -> None: ...

    @abc.abstractmethod
    def traverse(
        self,
        node: "pylpg.node.Node",
        relationship_type: str,
        direction: "pylpg.relationship.Direction",
    ) -> list[dict[str, typing.Any]]: ...

    @abc.abstractmethod
    def delete_all(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...
