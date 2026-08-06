"""Session for orchestrating object persistence."""

import contextlib
import typing

import pylpg.backend.base
import pylpg.node
import pylpg.relationship

_NodeEdges = dict[tuple[str, pylpg.relationship.Direction], list[pylpg.node.Node]]


class Session:
    """Orchestrates saving, deleting, and querying graph objects.

    Use as a context manager to ensure the backend connection is closed.

    Example:
        ```python
        with Session(backend) as session:
            alice = Person(name="Alice")
            session.save(alice)
        ```
    """

    def __init__(self, backend: pylpg.backend.base.Backend) -> None:
        self._backend = backend
        self._prefetch: dict[typing.Any, _NodeEdges] | None = None

    def __enter__(self) -> "Session":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: typing.Any,
    ) -> bool:
        self._backend.close()
        return False

    def execute_query(
        self,
        cypher: str,
        parameters: dict[str, typing.Any] | None = None,
        resolve_nodes: bool = False,
    ) -> list[dict[str, typing.Any]]:
        """Execute a raw Cypher query.

        When `resolve_nodes` is True, any driver node objects in the
        results are hydrated into `Node` instances.

        Example:
            ```python
            results = session.execute_query(
                "MATCH (n:Person) RETURN n",
                resolve_nodes=True,
            )
            for row in results:
                person = row["n"]  # a Person instance
            ```
        """
        results = self._backend.execute_query(cypher, parameters)
        if resolve_nodes:
            return [self._hydrate_row(row) for row in results]
        return results

    def save(
        self,
        item: (
            pylpg.node.Node
            | pylpg.relationship.Relationship
            | list[pylpg.node.Node | pylpg.relationship.Relationship]
        ),
    ) -> None:
        """Save a node, relationship, or a list of both.

        For single items, creates or updates depending on whether the
        item has already been saved. For lists, delegates to the
        backend's batch save strategy.

        Example:
            ```python
            session.save(alice)
            session.save(relationship)
            session.save([alice, bob, relationship])
            ```
        """
        self._prefetch = None
        if isinstance(item, pylpg.node.Node):
            self._save_node(item)
        elif isinstance(item, pylpg.relationship.Relationship):
            self._save_relationship(item)
        elif isinstance(item, list):
            self._backend.save_batch(items=item)
            for element in item:
                if isinstance(element, pylpg.node.Node):
                    element._session = self
                elif isinstance(element, pylpg.relationship.Relationship):
                    element.source._session = self
                    element.target._session = self

    def _save_node(self, node: pylpg.node.Node) -> None:
        if node.is_saved():
            result = self._backend.update_node(node=node)
        else:
            result = self._backend.create_node(node=node)
        if result:
            node._database_id = result["_database_id"]
        node._session = self

    def _save_relationship(self, relationship: pylpg.relationship.Relationship) -> None:
        if not relationship.source.is_saved():
            self._save_node(relationship.source)
        if not relationship.target.is_saved():
            self._save_node(relationship.target)
        if relationship.is_saved():
            result = self._backend.update_relationship(relationship=relationship)
        else:
            result = self._backend.create_relationship(relationship=relationship)
        if result:
            relationship._database_id = result["_database_id"]

    def delete(
        self,
        item: (
            pylpg.node.Node
            | pylpg.relationship.Relationship
            | list[pylpg.node.Node | pylpg.relationship.Relationship]
        ),
    ) -> None:
        """Delete a node, relationship, or a list of both.

        Example:
            ```python
            session.delete(alice)
            session.delete([alice, bob])
            ```
        """
        self._prefetch = None
        if isinstance(item, pylpg.node.Node):
            self._delete_node(item)
        elif isinstance(item, pylpg.relationship.Relationship):
            self._delete_relationship(item)
        elif isinstance(item, list):
            for element in item:
                self.delete(element)

    def _delete_node(self, node: pylpg.node.Node) -> None:
        if not node.is_saved():
            raise ValueError("Cannot delete unsaved node")
        self._backend.delete_node(node=node)
        node._database_id = None
        node._session = None

    def _delete_relationship(
        self, relationship: pylpg.relationship.Relationship
    ) -> None:
        if not relationship.is_saved():
            raise ValueError("Cannot delete unsaved relationship")
        self._backend.delete_relationship(relationship=relationship)
        relationship._database_id = None

    def delete_all(self) -> None:
        """Delete every node and relationship in the database.

        Delegates to the backend so each backend can apply its own
        strategy (e.g. FalkorDB drops the graph to clear stale label
        indexes that survive a plain `MATCH (n) DETACH DELETE n`).

        Example:
            ```python
            session.delete_all()
            ```
        """
        self._prefetch = None
        self._backend.delete_all()

    @contextlib.contextmanager
    def prefetch(self, roots: list[pylpg.node.Node]) -> typing.Iterator[None]:
        """Batch-load the subgraph reachable from `roots` into memory.

        Inside the block, traversal reads the snapshot instead of querying:
        one query per (relationship type, direction) per level, rather than
        one per node per field. Saving or deleting inside the block drops the
        snapshot; writes made through raw `execute_query` do not.

        Example:
            ```python
            with session.prefetch(roots=[alice, bob]):
                for friend in alice.friends.all():  # no query
                    ...
            ```
        """
        frontier = {node._database_id: node for node in roots if node.is_saved()}
        cache: dict[typing.Any, _NodeEdges] = {
            database_id: {} for database_id in frontier
        }
        while frontier:
            sources_by_key: dict[
                tuple[str, pylpg.relationship.Direction], set[typing.Any]
            ] = {}
            for node in frontier.values():
                for descriptor in type(node).__relationship_descriptors__.values():
                    key = (
                        descriptor._relationship_class.__type__,
                        descriptor._direction,
                    )
                    sources_by_key.setdefault(key, set()).add(node._database_id)
            next_frontier: dict[typing.Any, pylpg.node.Node] = {}
            for key, source_ids in sources_by_key.items():
                (relationship_type, direction) = key
                rows = self._backend.traverse_batch(
                    source_ids=list(source_ids),
                    relationship_type=relationship_type,
                    direction=direction,
                )
                for row in rows:
                    target = self._hydrate_node(
                        deserialized_node=self._backend.deserialize_node(
                            record=row["target"]
                        )
                    )
                    cache[row["source_id"]].setdefault(key, []).append(target)
                    if target._database_id not in cache:
                        cache[target._database_id] = {}
                        next_frontier[target._database_id] = target
            frontier = next_frontier
        self._prefetch = cache
        try:
            yield
        finally:
            self._prefetch = None

    def _traverse(
        self,
        node: pylpg.node.Node,
        relationship_type: str,
        direction: pylpg.relationship.Direction,
    ) -> list[pylpg.node.Node]:
        if self._prefetch is not None:
            node_edges = self._prefetch.get(node._database_id)
            if node_edges is not None:
                return list(node_edges.get((relationship_type, direction), ()))
        if not node.is_saved():
            raise ValueError("Cannot traverse from unsaved node")
        results = self._backend.traverse(
            node=node,
            relationship_type=relationship_type,
            direction=direction,
        )
        hydrated_results = self._hydrate_results(results)
        return [row["target"] for row in hydrated_results]

    def _hydrate_results(
        self, results: list[dict[str, typing.Any]]
    ) -> list[dict[str, typing.Any]]:
        hydrated_results = [self._hydrate_row(row) for row in results]
        return hydrated_results

    def _hydrate_row(self, row: dict[str, typing.Any]) -> dict[str, typing.Any]:
        hydrated_row: dict[str, typing.Any] = {}
        for key, item in row.items():
            hydrated_row[key] = self._hydrate_item(item)
        return hydrated_row

    def _hydrate_item(self, item: typing.Any) -> typing.Any:
        if self._backend.is_node(item):
            deserialized_node = self._backend.deserialize_node(record=item)
            return self._hydrate_node(deserialized_node=deserialized_node)
        if isinstance(item, list):
            return [self._hydrate_item(element) for element in item]
        if isinstance(item, dict):
            return {key: self._hydrate_item(element) for key, element in item.items()}
        return item

    def _hydrate_node(
        self,
        deserialized_node: dict[str, typing.Any],
    ) -> pylpg.node.Node:
        labels = deserialized_node["_labels"]
        cls = pylpg.node.Node.resolve_class(labels=labels)
        properties = {
            key: value
            for key, value in deserialized_node.items()
            if key in cls.__primitive_properties__
        }
        node = cls(**properties)
        node._database_id = deserialized_node["_database_id"]
        node._session = self
        return node
