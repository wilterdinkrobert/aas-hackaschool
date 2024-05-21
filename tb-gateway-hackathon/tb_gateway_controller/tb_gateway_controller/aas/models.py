from dataclasses import dataclass
from typing import List, Union, Dict


@dataclass
class SemanticKey:
    type: str
    value: str

    @classmethod
    def from_dict(cls, data):
        return cls(
            type=data.get("type", None),
            value=data.get("value", None)
        )


@dataclass
class SemanticId:
    type: str
    keys: List[SemanticKey]

    @classmethod
    def from_dict(cls, data):
        return cls(
            type=data.get("type", None),
            keys=[SemanticKey.from_dict(key) for key in data.get("keys", [])]
        )


def matches_semantic_id(semanticId: SemanticId, semantic_id: Union[str, List[str]]) -> bool:
    if semanticId is None:
        return False
    if isinstance(semantic_id, str):
        semantic_id = [semantic_id]
    return any([key.value in semantic_id for key in semanticId.keys])


def matches_semantic_id_raw(smc: Dict, semantic_id: str) -> bool:
    return any([key.get("value", None) == semantic_id for key in smc.get("semanticId", {}).get("keys", [])])


def get_property(smc: List[Dict], property_semantic_id: str) -> Dict:
    return next((x for x in smc if matches_semantic_id_raw(x, property_semantic_id)), {})


def get_property_value(smc: List[Dict], property_semantic_id: str, default: Union[str, None] = None) -> Union[str, None]:
    property = get_property(smc, property_semantic_id)
    value = property.get("value", default)
    if property.get("modelType", None) == "MultiLanguageProperty" and len(value) > 0:
        en_or_first = next((x for x in value if x.get("language", None) == "en"), value[0])
        return en_or_first.get("text", None)
    return value
