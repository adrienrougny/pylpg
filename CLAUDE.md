# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`pylpg` is a Python Object Graph Mapper (OGM) for labeled property graph databases (Neo4j, FalkorDB, FalkorDBLite). It maps Python classes to graph nodes/relationships and generates Cypher queries for CRUD operations.

## Development commands

```bash
# Install (uses uv + hatchling)
uv sync --all-extras

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Test (requires Docker for Neo4j and FalkorDB containers)
uv run pytest tests/ -v

# Test with coverage
uv run pytest tests/ --cov=pylpg --cov-report=term

# Test across Python versions
uv run tox -e py310-min,py311-min,py312-min,py313-min

# Build docs
uv run mkdocs build

# Serve docs locally
uv run mkdocs serve
```

## Code style

- Always use absolute imports: `import x` then `x.y`, never `from x import y`.
- Use full words for variable names, no abbreviations (e.g. `type_` not `t`, `annotation` not `ann`, `relationship` not `rel`). Exception: `cls` is allowed.
- No runtime value validation on properties — validation only happens at class definition time (type checking in `validate_properties`). The database backend is the ultimate authority on what values it accepts.
- Always run ruff check and ruff format after code changes.
- When calling functions across modules, use named parameters.

## Architecture

All source code is under `src/pylpg/`.

- **`node.py`** — `Node` base class with global label/name registries for hydration. Subclasses define graph nodes via type-annotated attributes. Labels default to class name.
- **`relationship.py`** — `Relationship` base class (requires `__type__`, `source`, `target`). Descriptor classes (`RelationshipTo`, `RelationshipFrom`, `RelationshipUndirected`) attach traversal and `connect()` capabilities to Node subclasses.
- **`types.py`** — Property type utilities. Extracts primitive properties and relationship descriptors, validates types at class definition time.
- **`cypher.py`** — Shared Cypher query builder used by cypher-based backends. Not imported by session.
- **`session.py`** — Orchestrates persistence via `save()`, `delete()`, `execute_query()`. Handles node hydration from query results.
- **`backend/`** — `Backend` ABC with full CRUD, batch, and traversal operations:
  - `Neo4jBackend` — uses UNWIND for batch operations
  - `FalkorDBBackend` — uses individual queries for batch (optimal for FalkorDB)
  - `FalkorDBLiteBackend` — embedded FalkorDB, inherits from FalkorDBBackend

## Design decisions

- **No custom exceptions** — plain `ValueError`/`TypeError` are sufficient.
- **No runtime value validation** — only class-definition-time type checking.
- **`__init_subclass__` over metaclass** — simpler, no metaclass conflicts.
- **Backend-specific batch strategies** — Neo4j uses UNWIND queries, FalkorDB uses individual queries. Each backend implements `save_batch()` optimally.
- **Global node registry** — `Node._label_registry` and `Node._name_registry` enable hydration without passing target classes through the call chain.
- **Session is orchestration only** — all database operations live on the backend. The session dispatches and handles Python-side concerns (ID mapping, hydration).
