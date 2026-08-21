"""Neo4j backend using the official Neo4j Python driver."""

import typing

import neo4j
import neo4j.graph

import pylpg.backend.base
import pylpg.cypher
import pylpg.node
import pylpg.relationship


class Neo4jBackend(pylpg.backend.base.Backend):
    """Backend for Neo4j databases.

    Uses UNWIND queries for batch operations, providing significant
    speedups over individual queries at scale.
    """

    _database_id_func_name = "elementId"

    def __init__(
        self,
        hostname: str = "localhost",
        port: int = 7687,
        database: str = "neo4j",
        username: str = "neo4j",
        password: str = "neo4j",
        protocol: str = "bolt",
        notifications_min_severity: typing.Literal["off", "information", "warning"]
        | None = None,
    ) -> None:
        uri = f"{protocol}://{hostname}:{port}"
        driver_kwargs: dict[str, typing.Any] = {"auth": (username, password)}
        if notifications_min_severity is not None:
            driver_kwargs["notifications_min_severity"] = (
                notifications_min_severity.upper()
            )
        self._driver = neo4j.GraphDatabase.driver(uri, **driver_kwargs)
        self._database = database

    def execute_query(
        self,
        cypher: str,
        parameters: dict[str, typing.Any] | None = None,
        transaction: neo4j.Transaction | None = None,
    ) -> list[dict[str, typing.Any]]:
        if transaction is not None:
            result = transaction.run(cypher, parameters=parameters or {})
            keys = result.keys()
            records = list(result)
        else:
            records, summary, keys = self._driver.execute_query(
                cypher, parameters_=parameters or {}, database_=self._database
            )
        return [dict(zip(keys, record.values())) for record in records]

    def is_node(self, value: typing.Any) -> bool:
        return isinstance(value, neo4j.graph.Node)

    def deserialize_node(self, record: typing.Any) -> dict[str, typing.Any]:
        properties = dict(record)
        properties["_labels"] = frozenset(record.labels)
        properties["_database_id"] = record.element_id
        return properties

    def deserialize_relationship(self, record: typing.Any) -> dict[str, typing.Any]:
        properties = dict(record)
        properties["_database_id"] = record.element_id
        properties["_start_id"] = record.start_node.element_id
        properties["_end_id"] = record.end_node.element_id
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
        new_node_groups: dict[frozenset[str], list[pylpg.node.Node]] = {}
        existing_node_groups: dict[frozenset[str], list[pylpg.node.Node]] = {}
        new_relationship_groups: dict[str, list[pylpg.relationship.Relationship]] = {}
        existing_relationship_groups: dict[
            str, list[pylpg.relationship.Relationship]
        ] = {}
        seen_nodes: set[int] = set()

        for item in items:
            if isinstance(item, pylpg.node.Node):
                self._triage_node(
                    node=item,
                    new_node_groups=new_node_groups,
                    existing_node_groups=existing_node_groups,
                    seen_nodes=seen_nodes,
                )
            elif isinstance(item, pylpg.relationship.Relationship):
                self._triage_node(
                    node=item.source,
                    new_node_groups=new_node_groups,
                    existing_node_groups=existing_node_groups,
                    seen_nodes=seen_nodes,
                )
                self._triage_node(
                    node=item.target,
                    new_node_groups=new_node_groups,
                    existing_node_groups=existing_node_groups,
                    seen_nodes=seen_nodes,
                )
                if not item.is_saved():
                    new_relationship_groups.setdefault(item.__type__, []).append(item)
                else:
                    existing_relationship_groups.setdefault(item.__type__, []).append(
                        item
                    )

        with self._driver.session(database=self._database) as session:
            with session.begin_transaction() as transaction:
                for new_nodes in new_node_groups.values():
                    self._batch_create_nodes(nodes=new_nodes, transaction=transaction)
                for existing_nodes in existing_node_groups.values():
                    self._batch_update_nodes(
                        nodes=existing_nodes, transaction=transaction
                    )
                for new_relationships in new_relationship_groups.values():
                    self._batch_create_relationships(
                        relationships=new_relationships, transaction=transaction
                    )
                for existing_relationships in existing_relationship_groups.values():
                    self._batch_update_relationships(
                        relationships=existing_relationships,
                        transaction=transaction,
                    )
                transaction.commit()

    def _triage_node(
        self,
        node: pylpg.node.Node,
        new_node_groups: dict[frozenset[str], list[pylpg.node.Node]],
        existing_node_groups: dict[frozenset[str], list[pylpg.node.Node]],
        seen_nodes: set[int],
    ) -> None:
        node_id = id(node)
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        if not node.is_saved():
            new_node_groups.setdefault(node.__labels__, []).append(node)
        else:
            existing_node_groups.setdefault(node.__labels__, []).append(node)

    def _batch_create_nodes(
        self,
        nodes: list[pylpg.node.Node],
        transaction: neo4j.Transaction,
    ) -> None:
        cypher, params = pylpg.cypher.build_batch_create_nodes_query(
            nodes=nodes, database_id_func_name=self._database_id_func_name
        )
        results = self.execute_query(cypher, params, transaction=transaction)
        temp_id_to_node = {node._temp_id: node for node in nodes}
        for row in results:
            node = temp_id_to_node[row["temp_id"]]
            node._database_id = row["_database_id"]

    def _batch_update_nodes(
        self,
        nodes: list[pylpg.node.Node],
        transaction: neo4j.Transaction,
    ) -> None:
        cypher, params = pylpg.cypher.build_batch_update_nodes_query(
            nodes=nodes, database_id_func_name=self._database_id_func_name
        )
        self.execute_query(cypher, params, transaction=transaction)

    def _batch_create_relationships(
        self,
        relationships: list[pylpg.relationship.Relationship],
        transaction: neo4j.Transaction,
    ) -> None:
        cypher, params = pylpg.cypher.build_batch_create_relationships_query(
            relationships=relationships,
            database_id_func_name=self._database_id_func_name,
        )
        results = self.execute_query(cypher, params, transaction=transaction)
        temp_id_to_relationship = {
            relationship._temp_id: relationship for relationship in relationships
        }
        for row in results:
            relationship = temp_id_to_relationship[row["temp_id"]]
            relationship._database_id = row["_database_id"]

    def _batch_update_relationships(
        self,
        relationships: list[pylpg.relationship.Relationship],
        transaction: neo4j.Transaction,
    ) -> None:
        cypher, params = pylpg.cypher.build_batch_update_relationships_query(
            relationships=relationships,
            database_id_func_name=self._database_id_func_name,
        )
        self.execute_query(cypher, params, transaction=transaction)

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
        self.execute_query(pylpg.cypher.build_delete_all_query())

    def close(self) -> None:
        self._driver.close()
