import unittest.mock

import pytest

import pylpg.backend.neo4j


@pytest.fixture(autouse=True)
def session():
    return None


def test_notifications_min_severity_forwarded_uppercased():
    with unittest.mock.patch("neo4j.GraphDatabase.driver") as driver_mock:
        pylpg.backend.neo4j.Neo4jBackend(
            password="x", notifications_min_severity="warning"
        )
    assert driver_mock.call_args.kwargs["notifications_min_severity"] == "WARNING"


def test_notifications_min_severity_omitted_by_default():
    with unittest.mock.patch("neo4j.GraphDatabase.driver") as driver_mock:
        pylpg.backend.neo4j.Neo4jBackend(password="x")
    assert "notifications_min_severity" not in driver_mock.call_args.kwargs
