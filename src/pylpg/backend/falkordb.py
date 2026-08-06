"""FalkorDB backend using the FalkorDB Python driver."""

import typing

import falkordb
import falkordb.node
import redis.exceptions

import pylpg.backend.base
import pylpg.cypher
import pylpg.node
import pylpg.relationship


class FalkorDBBackend(pylpg.backend.base.Backend):
    """Backend for FalkorDB server instances.

    Uses individual queries for batch operations, which is optimal
    for FalkorDB's in-memory architecture.
    """

    _database_id_func_name = "ID"

    def __init__(
        self,
        hostname: str = "localhost",
        port: int = 6379,
        database: str = "default",
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._db = falkordb.FalkorDB(
            host=hostname, port=port, username=username, password=password
        )
        self._graph = self._db.select_graph(database)

    def result_set_limit(self) -> int | None:
        # FalkorDB truncates any result set to RESULTSET_SIZE rows without
        # raising, so batched traversal must know the limit. A non-positive
        # value means unlimited. Not cached: the read costs ~47us, well under
        # a trivial round trip, and reading it every time picks up a runtime
        # GRAPH.CONFIG SET without needing a new session.
        # A server too old to know RESULTSET_SIZE has no cap to report.
        try:
            value = int(self._db.config_get("RESULTSET_SIZE"))
        except (redis.exceptions.ResponseError, TypeError, ValueError):
            value = -1
        return value if value > 0 else None

    def execute_query(
        self, cypher: str, parameters: dict[str, typing.Any] | None = None
    ) -> list[dict[str, typing.Any]]:
        result = self._graph.query(cypher, params=parameters or {})
        if result.result_set:
            header = [header_item[1] for header_item in result.header]
            return [dict(zip(header, row)) for row in result.result_set]
        return []

    def is_node(self, value: typing.Any) -> bool:
        return isinstance(value, falkordb.node.Node)

    def deserialize_node(self, record: typing.Any) -> dict[str, typing.Any]:
        properties = dict(record.properties)
        properties["_labels"] = frozenset(record.labels)
        properties["_database_id"] = record.id
        return properties

    def create_node(self, node: pylpg.node.Node) -> dict[str, typing.Any]:
        cypher, params = pylpg.cypher.build_create_node_query(
            node=node, database_id_func_name=self._database_id_func_name
        )
        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def update_node(self, node: pylpg.node.Node) -> dict[str, typing.Any]:
        cypher, params = pylpg.cypher.build_update_node_query(
            node=node, database_id_func_name=self._database_id_func_name
        )
        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def delete_node(self, node: pylpg.node.Node) -> None:
        cypher, params = pylpg.cypher.build_delete_node_query(
            node=node, database_id_func_name=self._database_id_func_name
        )
        self.execute_query(cypher, params)

    def create_relationship(
        self, relationship: pylpg.relationship.Relationship
    ) -> dict[str, typing.Any]:
        cypher, params = pylpg.cypher.build_create_relationship_query(
            relationship=relationship,
            database_id_func_name=self._database_id_func_name,
        )
        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def update_relationship(
        self, relationship: pylpg.relationship.Relationship
    ) -> dict[str, typing.Any]:
        cypher, params = pylpg.cypher.build_update_relationship_query(
            relationship=relationship,
            database_id_func_name=self._database_id_func_name,
        )
        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def delete_relationship(
        self, relationship: pylpg.relationship.Relationship
    ) -> None:
        cypher, params = pylpg.cypher.build_delete_relationship_query(
            relationship=relationship,
            database_id_func_name=self._database_id_func_name,
        )
        self.execute_query(cypher, params)

    def save_batch(
        self,
        items: list[pylpg.node.Node | pylpg.relationship.Relationship],
    ) -> None:
        nodes: list[pylpg.node.Node] = []
        relationships: list[pylpg.relationship.Relationship] = []
        for item in items:
            if isinstance(item, pylpg.node.Node):
                nodes.append(item)
            elif isinstance(item, pylpg.relationship.Relationship):
                if not item.source.is_saved():
                    nodes.append(item.source)
                if not item.target.is_saved():
                    nodes.append(item.target)
                relationships.append(item)
        for node in nodes:
            if not node.is_saved():
                row = self.create_node(node)
                if row:
                    node._database_id = row["_database_id"]
            else:
                self.update_node(node)
        for relationship in relationships:
            if not relationship.is_saved():
                row = self.create_relationship(relationship)
                if row:
                    relationship._database_id = row["_database_id"]
            else:
                self.update_relationship(relationship)

    def traverse(
        self,
        node: pylpg.node.Node,
        relationship_type: str,
        direction: pylpg.relationship.Direction,
    ) -> list[dict[str, typing.Any]]:
        cypher, params = pylpg.cypher.build_traverse_query(
            node=node,
            relationship_type=relationship_type,
            direction=direction,
            database_id_func_name=self._database_id_func_name,
        )
        return self.execute_query(cypher, params)

    def delete_all(self) -> None:
        # FalkorDB's DETACH DELETE leaves stale label-index entries that
        # surface as phantom nodes on subsequent MATCH (n:Label) queries.
        # Drop the entire graph and re-select instead.
        try:
            self._graph.delete()
        except redis.exceptions.ResponseError:
            pass
        self._graph = self._db.select_graph(self._graph.name)

    def close(self) -> None:
        pass
