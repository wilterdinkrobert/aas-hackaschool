from dataclasses import dataclass
from enum import Enum
from typing import List, Union, Dict

from tb_gateway_controller.aas.models import SemanticId, get_property_value, get_property, matches_semantic_id_raw, \
    matches_semantic_id, has_property

AID_SUBMODEL_SEMANTIC_ID = "https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel"


class InterfaceType(Enum):
    UNKNOWN = "UNKNOWN",
    MQTT = "MQTT"


@dataclass
class EndpointMetadata:
    base: str

    @classmethod
    def from_dict(cls, data):
        return cls(base=get_property_value(data, "https://www.w3.org/2019/wot/td#base"))


@dataclass
class Forms:
    href: str
    contentType: str

    @classmethod
    def from_dict(cls, data):
        return cls(href=get_property_value(data, "https://www.w3.org/2019/wot/hypermedia#hasTarget"),
                   contentType=get_property_value(data, "https://www.w3.org/2019/wot/hypermedia#forContentType"))


@dataclass
class Property:
    idShort: str
    key: str
    type: str
    title: str
    unit: str
    properties: List["Property"]
    forms: Forms

    @classmethod
    def from_dict(cls, data):
        semanticId = SemanticId.from_dict(data.get("semanticId", {}))
        if not matches_semantic_id(semanticId, ["https://admin-shell.io/idta/AssetInterfaceDescription/1/0/PropertyDefinition", "https://www.w3.org/2019/wot/json-schema#propertyName"]):
            raise ValueError("semanticId mismatch")

        value = data.get("value", [])

        return cls(idShort=data.get("idShort", None),
                   key=get_property_value(value, "https://admin-shell.io/idta/AssetInterfacesDescription/1/0/key"),
                   type=get_property_value(value, "https://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                   title=get_property_value(value, "https://www.w3.org/2019/wot/td#title"),
                   unit=get_property_value(value, "https://schema.org/unitCode"),
                   properties=[Property.from_dict(i) for i in get_property(value, "https://www.w3.org/2019/wot/json-schema#properties").get("value", [])],
                   forms=Forms.from_dict(get_property(value, "https://www.w3.org/2019/wot/td#hasForm").get("value", None)) if has_property(value, "https://www.w3.org/2019/wot/td#hasForm") else None)


@dataclass
class InteractionMetadata:
    properties: List[Property]

    @classmethod
    def from_dict(cls, data):
        return cls(properties=[Property.from_dict(i) for i in get_property(data, "https://www.w3.org/2019/wot/td#PropertyAffordance").get("value", [])])


@dataclass
class Interface:
    idShort: str
    type: InterfaceType
    title: str
    created: str
    modified: str
    observable: bool
    endpointMetadata: EndpointMetadata
    interactionMetadata: InteractionMetadata

    @classmethod
    def from_dict(cls, data):
        semanticId = SemanticId.from_dict(data.get("semanticId", {}))
        if (matches_semantic_id(semanticId, "http://www.w3.org/2011/mqtt")):
            type = InterfaceType.MQTT
        else:
            type = InterfaceType.UNKNOWN

        value = data.get("value", [])
        observable = get_property_value(value, "https://www.w3.org/2019/wot/td#isObservable", "false").lower() == "true",

        return cls(
            idShort=data.get("idShort"),
            type=type,
            title=get_property_value(value, "https://www.w3.org/2019/wot/td#title"),
            created=get_property_value(value, "http://purl.org/dc/terms/created"),
            modified=get_property_value(value, "http://purl.org/dc/terms/modified"),
            observable=observable,
            endpointMetadata=EndpointMetadata.from_dict(get_property(value, "https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata").get("value", {})),
            interactionMetadata=InteractionMetadata.from_dict(get_property(value, "https://admin-shell.io/idta/AssetInterfacesDescription/1/0/InteractionMetadata").get("value", []))
        )


@dataclass
class AIDSubmodel:
    idShort: str
    id: str
    interfaces: List[Interface]

    @classmethod
    def from_dict(cls, data):
        semanticId = SemanticId.from_dict(data.get("semanticId", {}))

        if not matches_semantic_id(semanticId, AID_SUBMODEL_SEMANTIC_ID):
            raise ValueError("semanticId mismatch")

        return cls(
            idShort=data.get("idShort"),
            id=data.get("id"),
            interfaces=[Interface.from_dict(i) for i in data.get("submodelElements") if matches_semantic_id_raw(i, "https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface")]
        )
