"""Abstract base class for database backends."""

import abc
import typing

import pylpg.cypher

if typing.TYPE_CHECKING:
    import pylpg.node
    import pylpg.relationship


class Backend(abc.ABC):
    """Abstract base class that all database backends must implement.

    Backends handle all direct database operations: CRUD for nodes and
    relationships, batch operations, traversal, and query execution.
    """

    _database_id_func_name: typing.ClassVar[str]

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

    def result_set_limit(self) -> int | None:
        """Maximum number of rows a single query may return.

        Returns None when the backend imposes no limit. Backends that
        silently truncate oversized result sets (FalkorDB caps at
        `RESULTSET_SIZE`, 10000 by default) must report their limit here
        so `traverse_batch` can split batches instead of losing rows.
        """
        return None

    def traverse_batch(
        self,
        source_ids: list[typing.Any],
        relationship_type: str,
        direction: "pylpg.relationship.Direction",
    ) -> list[dict[str, typing.Any]]:
        """Traverse from many source nodes at once.

        Splits the batch and retries whenever a result set comes back at
        the backend's row limit, since such a result set may have been
        silently truncated.
        """
        limit = self.result_set_limit()
        rows: list[dict[str, typing.Any]] = []
        pending = [list(source_ids)]
        while pending:
            chunk = pending.pop()
            if not chunk:
                continue
            chunk_rows = self._traverse_batch_chunk(
                source_ids=chunk,
                relationship_type=relationship_type,
                direction=direction,
            )
            if limit is not None and len(chunk_rows) >= limit:
                if len(chunk) == 1:
                    raise ValueError(
                        f"Node {chunk[0]} has at least {limit} '{relationship_type}' "
                        f"relationships, which reaches this backend's result set "
                        f"limit of {limit} rows. The result would be silently "
                        f"truncated. Raise the backend's limit (for FalkorDB: "
                        f"GRAPH.CONFIG SET RESULTSET_SIZE) to traverse this node."
                    )
                middle = len(chunk) // 2
                pending.append(chunk[:middle])
                pending.append(chunk[middle:])
                continue
            rows.extend(chunk_rows)
        return rows

    def _traverse_batch_chunk(
        self,
        source_ids: list[typing.Any],
        relationship_type: str,
        direction: "pylpg.relationship.Direction",
    ) -> list[dict[str, typing.Any]]:
        cypher, params = pylpg.cypher.build_batch_traverse_query(
            source_ids=source_ids,
            relationship_type=relationship_type,
            direction=direction,
            database_id_func_name=self._database_id_func_name,
        )
        return self.execute_query(cypher, params)

    @abc.abstractmethod
    def delete_all(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...
