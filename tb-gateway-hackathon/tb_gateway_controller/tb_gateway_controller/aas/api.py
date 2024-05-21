from tb_gateway_controller.aas.utils import get_endpoint_href
from tb_gateway_controller.utils import base64encode


class AASNotFoundError(Exception):
    pass


class AASAPIError(Exception):
    pass


class SubmodelNotFoundError(Exception):
    pass


async def get_aas_descriptor_from_registry(session, registry_base_url: str, aasIdentifier: str):
    query=f"{registry_base_url}/shell-descriptors/{base64encode(aasIdentifier)}"
    async with session.get(query) as resp:
        if resp.status == 200:
            return await resp.json()
    raise AASNotFoundError(aasIdentifier)


async def resolve_aas_endpoint_on_registry(session, registry_base_url: str, aasIdentifier: str):
    data = await get_aas_descriptor_from_registry(session, registry_base_url, aasIdentifier)
    try:
        return get_endpoint_href(data)
    except KeyError as e:
        raise AASAPIError(f"KeyError: {e}")


async def get_aas_from_env(session, aas_url: str):
    query=f"{aas_url}"
    async with session.get(query) as resp:
        if resp.status == 200:
            return await resp.json()
    raise AASNotFoundError(aas_url)


async def get_submodel_descriptor_from_registry(session, registry_base_url: str, submodelIdentifier: str):
    query=f"{registry_base_url}/submodel-descriptors/{base64encode(submodelIdentifier)}"
    async with session.get(query) as resp:
        if resp.status == 200:
            return await resp.json()
    raise SubmodelNotFoundError(submodelIdentifier)


async def get_submodel_from_env(session, submodel_url: str):
    query=f"{submodel_url}"
    async with session.get(query) as resp:
        if resp.status == 200:
            return await resp.json()
    raise SubmodelNotFoundError(submodel_url)