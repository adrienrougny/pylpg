import tests.models


def test_delete_all_clears_label_index(session):
    backend = session._backend
    for _ in range(3):
        for index in range(5):
            session.save(tests.models.Person(name=f"bulk-{index}"))
        backend.delete_all()
        session.save(tests.models.Person(name="solo", age=42))
        rows = backend.execute_query(
            "MATCH (n:Person) RETURN labels(n) AS labels, properties(n) AS props"
        )
        assert len(rows) == 1
        assert list(rows[0]["labels"]) == ["Person"]
        assert dict(rows[0]["props"]) == {"name": "solo", "age": 42}
        backend.delete_all()
