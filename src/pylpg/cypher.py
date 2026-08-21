import typing

import pylpg.relationship
import pylpg.node


def _labels_str(labels: frozenset[str]) -> str:
    return ":".join(labels)


def build_create_node_query(
    node: pylpg.node.Node, database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    labels = _labels_str(node.__labels__)
    cypher = (
        f"CREATE (node:{labels}) "
        f"SET node = $properties "
        f"RETURN {database_id_func_name}(node) AS _database_id"
    )
    params = {"properties": node.to_dict()}
    return cypher, params


def build_update_node_query(
    node: pylpg.node.Node, database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    labels = _labels_str(node.__labels__)
    cypher = (
        f"MATCH (node:{labels}) "
        f"WHERE {database_id_func_name}(node) = $node_id "
        f"SET node = $properties "
        f"RETURN {database_id_func_name}(node) AS _database_id"
    )
    params = {"node_id": node._database_id, "properties": node.to_dict()}
    return cypher, params


def build_delete_node_query(
    node: pylpg.node.Node, database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    labels = _labels_str(node.__labels__)
    cypher = (
        f"MATCH (node:{labels}) "
        f"WHERE {database_id_func_name}(node) = $node_id "
        f"DETACH DELETE node"
    )
    params = {"node_id": node._database_id}
    return cypher, params


def build_create_relationship_query(
    relationship: pylpg.relationship.Relationship, database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    relationship_type = relationship.__type__
    cypher = (
        f"MATCH (source) WHERE {database_id_func_name}(source) = $source_id "
        f"MATCH (target) WHERE {database_id_func_name}(target) = $target_id "
        f"CREATE (source)-[relationship:{relationship_type}]->(target) "
        f"SET relationship = $properties "
        f"RETURN {database_id_func_name}(relationship) AS _database_id"
    )
    params = {
        "source_id": relationship.source._database_id,
        "target_id": relationship.target._database_id,
        "properties": relationship.to_dict(),
    }
    return cypher, params


def build_update_relationship_query(
    relationship: pylpg.relationship.Relationship, database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    relationship_type = relationship.__type__
    cypher = (
        f"MATCH ()-[relationship:{relationship_type}]->() "
        f"WHERE {database_id_func_name}(relationship) = $relationship_id "
        f"SET relationship = $properties "
        f"RETURN {database_id_func_name}(relationship) AS _database_id"
    )
    params = {
        "relationship_id": relationship._database_id,
        "properties": relationship.to_dict(),
    }
    return cypher, params


def build_delete_relationship_query(
    relationship: pylpg.relationship.Relationship, database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    relationship_type = relationship.__type__
    cypher = (
        f"MATCH ()-[relationship:{relationship_type}]->() "
        f"WHERE {database_id_func_name}(relationship) = $relationship_id "
        f"DELETE relationship"
    )
    params = {"relationship_id": relationship._database_id}
    return cypher, params


def build_batch_create_nodes_query(
    nodes: list[pylpg.node.Node], database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    labels = _labels_str(nodes[0].__labels__)
    cypher = (
        f"UNWIND $batch AS row "
        f"CREATE (node:{labels}) "
        f"SET node = row.properties "
        f"RETURN {database_id_func_name}(node) AS _database_id, row.temp_id AS temp_id"
    )
    batch = [{"properties": node.to_dict(), "temp_id": node._temp_id} for node in nodes]
    return cypher, {"batch": batch}


def build_batch_update_nodes_query(
    nodes: list[pylpg.node.Node], database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    labels = _labels_str(nodes[0].__labels__)
    cypher = (
        f"UNWIND $batch AS row "
        f"MATCH (node:{labels}) "
        f"WHERE {database_id_func_name}(node) = row.id "
        f"SET node = row.properties "
        f"RETURN {database_id_func_name}(node) AS _database_id, row.temp_id AS temp_id"
    )
    batch = [
        {
            "id": node._database_id,
            "properties": node.to_dict(),
            "temp_id": node._temp_id,
        }
        for node in nodes
    ]
    return cypher, {"batch": batch}


def build_batch_create_relationships_query(
    relationships: list[pylpg.relationship.Relationship], database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    relationship_type = relationships[0].__type__
    cypher = (
        f"UNWIND $batch AS row "
        f"MATCH (source) WHERE {database_id_func_name}(source) = row.source_id "
        f"MATCH (target) WHERE {database_id_func_name}(target) = row.target_id "
        f"CREATE (source)-[relationship:{relationship_type}]->(target) "
        f"SET relationship = row.properties "
        f"RETURN {database_id_func_name}(relationship) AS _database_id, row.temp_id AS temp_id"
    )
    batch = [
        {
            "source_id": relationship.source._database_id,
            "target_id": relationship.target._database_id,
            "properties": relationship.to_dict(),
            "temp_id": relationship._temp_id,
        }
        for relationship in relationships
    ]
    return cypher, {"batch": batch}


def build_batch_update_relationships_query(
    relationships: list[pylpg.relationship.Relationship], database_id_func_name: str
) -> tuple[str, dict[str, typing.Any]]:
    relationship_type = relationships[0].__type__
    cypher = (
        f"UNWIND $batch AS row "
        f"MATCH ()-[relationship:{relationship_type}]->() "
        f"WHERE {database_id_func_name}(relationship) = row.id "
        f"SET relationship = row.properties "
        f"RETURN {database_id_func_name}(relationship) AS _database_id, row.temp_id AS temp_id"
    )
    batch = [
        {
            "id": relationship._database_id,
            "properties": relationship.to_dict(),
            "temp_id": relationship._temp_id,
        }
        for relationship in relationships
    ]
    return cypher, {"batch": batch}


def build_delete_all_query() -> str:
    return "MATCH (node) DETACH DELETE node"


def _traverse_pattern(
    relationship_type: str, direction: pylpg.relationship.Direction
) -> str:
    if direction == pylpg.relationship.Direction.OUTGOING:
        return f"(source)-[relationship:{relationship_type}]->(target)"
    if direction == pylpg.relationship.Direction.INCOMING:
        return f"(source)<-[relationship:{relationship_type}]-(target)"
    return f"(source)-[relationship:{relationship_type}]-(target)"


def build_traverse_query(
    node: pylpg.node.Node,
    relationship_type: str,
    direction: pylpg.relationship.Direction,
    database_id_func_name: str,
) -> tuple[str, dict[str, typing.Any]]:
    pattern = _traverse_pattern(
        relationship_type=relationship_type, direction=direction
    )
    cypher = (
        f"MATCH {pattern} "
        f"WHERE {database_id_func_name}(source) = $source_id "
        f"RETURN target, relationship"
    )
    params = {"source_id": node._database_id}
    return cypher, params


def build_batch_traverse_query(
    source_ids: list[typing.Any],
    relationship_type: str,
    direction: pylpg.relationship.Direction,
    database_id_func_name: str,
) -> tuple[str, dict[str, typing.Any]]:
    pattern = _traverse_pattern(
        relationship_type=relationship_type, direction=direction
    )
    cypher = (
        f"UNWIND $source_ids AS source_id "
        f"MATCH {pattern} "
        f"WHERE {database_id_func_name}(source) = source_id "
        f"RETURN source_id, target, relationship"
    )
    return cypher, {"source_ids": source_ids}
