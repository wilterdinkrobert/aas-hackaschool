from dataclasses import dataclass
from enum import Enum
from typing import List, Union, Dict

from tb_gateway_controller.aas.models import SemanticId, matches_semantic_id, matches_semantic_id_raw, \
    get_property_value

DNP_SUBMODEL_SEMANTIC_ID = "https://admin-shell.io/zvei/nameplate/2/0/Nameplate"

@dataclass
class DigitalNameplateSubmodel:
    idShort: str
    id: str

    URIOfTheProduct: str
    SerialNumber: str
    ManufacturerName: str
    ManufacturerProductType: str
    # FIXME: DNP contains more properties and SMCs

    @classmethod
    def from_dict(cls, data):
        semanticId = SemanticId.from_dict(data.get("semanticId", {}))

        if not matches_semantic_id(semanticId, DNP_SUBMODEL_SEMANTIC_ID):
            raise ValueError("semanticId mismatch")

        value = data.get("submodelElements", [])

        return cls(
            idShort=data.get("idShort"),
            id=data.get("id"),
            URIOfTheProduct=get_property_value(value, "0173-1#02-AAY811#001"),
            SerialNumber=get_property_value(value, "0173-1#02-AAM556#002"),
            ManufacturerName=get_property_value(value, "0173-1#02-AAO677#002"),
            ManufacturerProductType=get_property_value(value, "0173-1#02-AAO057#002")
        )