from typing import List, Dict, Union


def get_submodel_references(aas) -> List[str]:
    assert "submodels" in aas
    return [k['value'] for ref in aas['submodels'] for k in ref['keys'] if k['type'] == 'Submodel']


def get_endpoint_href(data) -> str:
    return data["endpoints"][0]["protocolInformation"]["href"]

