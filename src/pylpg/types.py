"""Property type utilities for validation and introspection."""

import types
import typing


ALLOWED_PRIMITIVE_TYPES = (str, int, float, bool, type(None))


def _is_allowed_type(type_: typing.Any) -> bool:
    if type_ in ALLOWED_PRIMITIVE_TYPES:
        return True
    origin = typing.get_origin(type_)
    if origin is list:
        args = typing.get_args(type_)
        return len(args) == 1 and args[0] in ALLOWED_PRIMITIVE_TYPES
    return False


def _flatten_type(type_: typing.Any) -> list[typing.Any]:
    if isinstance(type_, types.UnionType):
        return list(type_.__args__)
    origin = typing.get_origin(type_)
    if origin is typing.Union:
        return list(typing.get_args(type_))
    return [type_]


def validate_properties(properties: dict[str, typing.Any]) -> None:
    for property_name, property_type in properties.items():
        flat = _flatten_type(property_type)
        for property_type in flat:
            if not _is_allowed_type(property_type):
                type_name = (
                    property_type.__name__
                    if hasattr(property_type, "__name__")
                    else str(property_type)
                )
                raise ValueError(
                    f"Property '{property_name}': unsupported type {type_name}"
                )


def get_primitive_properties(cls: type) -> dict[str, typing.Any]:
    import pylpg.relationship

    type_hints = typing.get_type_hints(cls)
    properties: dict[str, typing.Any] = {}
    for attribute_name, attribute_type in type_hints.items():
        if attribute_name.startswith("_"):
            continue
        attribute_value = getattr(cls, attribute_name, None)
        if isinstance(attribute_value, pylpg.relationship.RelationshipDescriptor):
            continue
        properties[attribute_name] = attribute_type
    return properties


def get_relationship_descriptors(cls: type) -> dict[str, typing.Any]:
    import pylpg.relationship

    relationship_descriptors: dict[str, typing.Any] = {}
    for attribute_name in dir(cls):
        if attribute_name.startswith("_"):
            continue
        attribute_value = getattr(cls, attribute_name, None)
        if isinstance(attribute_value, pylpg.relationship.RelationshipDescriptor):
            relationship_descriptors[attribute_name] = attribute_value
    return relationship_descriptors
