import os
import urllib.parse

import pytest

import testcontainers.neo4j
import testcontainers.core.container
import testcontainers.core.waiting_utils

import pylpg.active_session
import pylpg.backend.neo4j
import pylpg.backend.falkordb
import pylpg.backend.falkordblite
import pylpg.session

import importlib.util

HAS_FALKORDBLITE = importlib.util.find_spec("redislite") is not None


@pytest.fixture(scope="session")
def neo4j_container():
    container = testcontainers.neo4j.Neo4jContainer("neo4j:5")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def falkordb_container():
    container = testcontainers.core.container.DockerContainer(
        "falkordb/falkordb:latest"
    )
    container.with_exposed_ports(6379)
    container.start()
    testcontainers.core.waiting_utils.wait_for_logs(
        container, "Ready to accept connections"
    )
    yield container
    container.stop()


@pytest.fixture(scope="session")
def neo4j_backend(neo4j_container):
    if os.environ.get("CI"):
        return pylpg.backend.neo4j.Neo4jBackend(
            hostname="localhost",
            port=7687,
            username="neo4j",
            password="testpassword",
        )
    parsed = urllib.parse.urlparse(neo4j_container.get_connection_url())
    return pylpg.backend.neo4j.Neo4jBackend(
        hostname=parsed.hostname,
        port=parsed.port,
        protocol=parsed.scheme,
        username=neo4j_container.username,
        password=neo4j_container.password,
    )


@pytest.fixture(scope="session")
def falkordb_backend(falkordb_container):
    if os.environ.get("CI"):
        return pylpg.backend.falkordb.FalkorDBBackend(
            hostname="localhost",
            port=6379,
            database="test",
        )
    return pylpg.backend.falkordb.FalkorDBBackend(
        hostname=falkordb_container.get_container_host_ip(),
        port=int(falkordb_container.get_exposed_port(6379)),
        database="test",
    )


@pytest.fixture(scope="session")
def falkordblite_backend():
    if not HAS_FALKORDBLITE:
        pytest.skip("falkordblite not installed")
    backend = pylpg.backend.falkordblite.FalkorDBLiteBackend(
        path="/tmp/test_falkordblite.db",
        database="test",
    )
    yield backend
    backend.close()


def _backend_params():
    params = ["neo4j", "falkordb"]
    if HAS_FALKORDBLITE:
        params.append("falkordblite")
    return params


@pytest.fixture(params=_backend_params())
def backend(request, neo4j_backend, falkordb_backend, falkordblite_backend):
    if request.param == "neo4j":
        return neo4j_backend
    elif request.param == "falkordb":
        return falkordb_backend
    return falkordblite_backend


@pytest.fixture(autouse=True)
def session(backend):
    session = pylpg.session.Session(backend)
    pylpg.active_session.set_active_session(session)
    yield session
    pylpg.active_session.set_active_session(None)
