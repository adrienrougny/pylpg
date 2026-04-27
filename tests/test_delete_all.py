import unittest.mock

import pylpg.session
import tests.models


def test_delete_all_clears_label_index(session):
    for _ in range(3):
        for index in range(5):
            session.save(tests.models.Person(name=f"bulk-{index}"))
        session.delete_all()
        session.save(tests.models.Person(name="solo", age=42))
        rows = session.execute_query(
            "MATCH (n:Person) RETURN labels(n) AS labels, properties(n) AS props"
        )
        assert len(rows) == 1
        assert list(rows[0]["labels"]) == ["Person"]
        assert dict(rows[0]["props"]) == {"name": "solo", "age": 42}
        session.delete_all()


def test_session_delete_all_delegates_to_backend():
    backend = unittest.mock.MagicMock()
    session = pylpg.session.Session(backend)
    session.delete_all()
    backend.delete_all.assert_called_once_with()
