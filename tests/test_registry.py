import pylpg.node

import tests.models


def test_label_registry():
    assert pylpg.node.Node._label_registry[frozenset({"Person"})] is tests.models.Person
    assert pylpg.node.Node._label_registry[frozenset({"Animal"})] is tests.models.Animal


def test_name_registry():
    assert pylpg.node.Node._name_registry["Person"] is tests.models.Person
    assert pylpg.node.Node._name_registry["Animal"] is tests.models.Animal


def test_resolve_class():
    assert pylpg.node.Node.resolve_class(frozenset({"Person"})) is tests.models.Person


def test_resolve_class_unknown_raises():
    try:
        pylpg.node.Node.resolve_class(frozenset({"UnknownLabel"}))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
