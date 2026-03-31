"""FalkorDBLite embedded backend, no server required."""

import pylpg.backend.falkordb


class FalkorDBLiteBackend(pylpg.backend.falkordb.FalkorDBBackend):
    """Embedded FalkorDB backend using FalkorDBLite.

    Runs FalkorDB as a local subprocess with file-based persistence.
    No external server required. Requires the `falkordblite` extra.
    """

    def __init__(
        self, path: str = "/tmp/falkordblite.db", database: str = "default"
    ) -> None:
        import redislite

        self._db = redislite.FalkorDB(path)
        self._graph = self._db.select_graph(database)

    def close(self) -> None:
        self._db.close()
