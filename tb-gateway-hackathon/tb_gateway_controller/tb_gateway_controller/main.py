import argparse
import asyncio
import logging
import os.path
import traceback
from pprint import pprint
from typing import Optional, Dict, List
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientConnectorError

from tb_gateway_controller.aas.aid.models import AID_SUBMODEL_SEMANTIC_ID, AIDSubmodel, matches_semantic_id_raw, \
    InterfaceType
from tb_gateway_controller.aas.api import resolve_aas_endpoint_on_registry, get_aas_from_env, \
    get_submodel_descriptor_from_registry, get_submodel_from_env, SubmodelNotFoundError, AASAPIError, AASNotFoundError
from tb_gateway_controller.aas.dnp.models import DNP_SUBMODEL_SEMANTIC_ID, DigitalNameplateSubmodel
from tb_gateway_controller.aas.utils import get_submodel_references, get_endpoint_href
from tb_gateway_controller.gateway.config_writer import ConfigWriter
from tb_gateway_controller.gateway.models import Gateway, Connector, MQTT, MQTTTopic, Timeseries

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger("main")

configs: Dict[str, AIDSubmodel] = {}
config_writer = ConfigWriter()
feature_assume_tsv_wrapper = False

async def get_submodel_descriptors(session, aas_registry, sm_registry, aas_id):
    resolved_aas_url = await resolve_aas_endpoint_on_registry(session, aas_registry, aas_id)
    aas = await get_aas_from_env(session, resolved_aas_url)
    return await asyncio.gather(*[get_submodel_descriptor_from_registry(session, sm_registry, submodel_reference) for submodel_reference in get_submodel_references(aas)], return_exceptions=True)


async def scrape_digital_nameplate(session, aas_registry, sm_registry, aas_id):
    submodel_descriptors = await get_submodel_descriptors(session, aas_registry, sm_registry, aas_id)
    dnp_descriptors = [descriptor for descriptor in submodel_descriptors if matches_semantic_id_raw(descriptor, DNP_SUBMODEL_SEMANTIC_ID)]
    assert len(dnp_descriptors) <= 1
    dnp_submodels = await asyncio.gather(*[get_submodel_from_env(session, get_endpoint_href(dnp_descriptor)) for dnp_descriptor in dnp_descriptors], return_exceptions=True)
    return DigitalNameplateSubmodel.from_dict(dnp_submodels[0]) if len(dnp_descriptors) == 1 else None


async def scrape_asset_interface_descriptions(session, aas_registry, sm_registry, aas_id):
    submodel_descriptors = await get_submodel_descriptors(session, aas_registry, sm_registry, aas_id)
    aid_descriptors = [descriptor for descriptor in submodel_descriptors if matches_semantic_id_raw(descriptor, AID_SUBMODEL_SEMANTIC_ID)]
    aid_submodels = await asyncio.gather(*[get_submodel_from_env(session, get_endpoint_href(aid_descriptor)) for aid_descriptor in aid_descriptors], return_exceptions=True)
    return [AIDSubmodel.from_dict(sm) for sm in aid_submodels]


def convert_to_timeseries(p, prefix_key=None, prefix_value=None, level=0) -> List[Timeseries]:
    ts_key = f"{prefix_key}_{p.idShort}" if prefix_key is not None else p.idShort
    if level == 0:
        if len(p.properties) > 0:
            ts_value = None
        else:
            if feature_assume_tsv_wrapper:
                ts_value = "value"
            else:
                # Note: If the gateway complains about 'could not convert string to float' you either need to extend the AID model tree or change this AID property.type to string.
                ts_value = "[:]"
    else:
        ts_value = f"{prefix_value}.{p.idShort}" if prefix_value is not None else p.idShort

    ts_type = p.type if p.type != "number" else "float"

    if p.type == "array":
        # The gateway cannot deconstruct objects with array fields at the moment, hence store them in 1 string
        return [Timeseries("string", ts_key, "${" + ts_value + "}")]
    elif ts_type == "object":
        timeseries = []
        for p_child in p.properties:
            timeseries.extend(convert_to_timeseries(p_child, ts_key, ts_value, level+1))
        return timeseries
    else:
        assert len(p.properties) == 0
        return [Timeseries(ts_type, ts_key, "${" + ts_value + "}")]


def convert_to_topic(property, dnp):
    return [MQTTTopic(property.forms.href, convert_to_timeseries(property), f"{dnp.ManufacturerName}-{dnp.ManufacturerProductType}-{dnp.SerialNumber}")]


def convert_to_connectors(dnp: DigitalNameplateSubmodel, aid: AIDSubmodel) -> List[Connector]:
    connectors = []
    for interface in aid.interfaces:
        if interface.type == InterfaceType.MQTT:
            base = interface.endpointMetadata.base
            url = urlparse(base if base.startswith("mqtt://") else f"mqtt://{base}")
            topics = []
            for property in interface.interactionMetadata.properties:
                topics.extend(convert_to_topic(property, dnp))
            mqtt = MQTT(f"{url.hostname}", url.port, topics)
            connectors.append(Connector("mqtt", interface.idShort, mqtt))
        else:
            raise NotImplementedError("Type not implemented yet")
    return connectors


async def restart_tb_gateway_service():
    log.info("RESTARTING thingsboard-gateway.service")
    cmd = "supervisorctl restart thingsboard-gateway"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        log.info("thingsboard-gateway service restarted")
    else:
        log.warning(f"{cmd!r} exited with {proc.returncode}")

    if stdout:
        log.info(f"{stdout.decode()}")
    if stderr:
        log.error(f"{stderr.decode()}")


async def main(args: Optional[argparse.Namespace]) -> None:
    global feature_assume_tsv_wrapper
    feature_assume_tsv_wrapper = args.feature_assume_tsv_wrapper

    async with aiohttp.ClientSession() as session:
        if not os.path.exists(args.gateway_config):
            os.mkdir(args.gateway_config)

        dnp_submodel = None
        while dnp_submodel is None:
            try:
                dnp_submodel = await scrape_digital_nameplate(session, args.aas_registry, args.submodel_registry, args.gateway_aas_id)
                pprint(dnp_submodel)
            except Exception as e:
                log.error(f"Exception: {type(e)}: {str(e)}")
                if not isinstance(e, (ClientConnectorError, AASNotFoundError, AASAPIError, SubmodelNotFoundError)):
                    log.error(traceback.format_exc())
                await asyncio.sleep(10)

        while True:
            try:
                aid_submodels = await scrape_asset_interface_descriptions(session, args.aas_registry, args.submodel_registry, args.gateway_aas_id)
                updated = False
                for aid in aid_submodels:
                    if aid.id not in configs.keys() or configs[aid.id] != aid:
                        configs[aid.id] = aid
                        connectors = convert_to_connectors(dnp_submodel, aid)
                        config_writer.write_connectors(args.gateway_config, connectors)
                        updated = True
                if updated:
                    config_writer.write_gateway(args.gateway_config, Gateway(args.thingsboard_host, args.thingsboard_port, args.thingsboard_access_token, connectors))
                    pprint(aid_submodels)
                    await restart_tb_gateway_service()
            except Exception as e:
                log.error(f"Exception: {type(e)}: {str(e)}")
                if not isinstance(e, (ClientConnectorError, AASNotFoundError, AASAPIError, SubmodelNotFoundError)):
                    log.error(traceback.format_exc())
            await asyncio.sleep(10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Control pane for thingsboard gateway')
    parser.add_argument(
        '--gateway-aas-id', '-g', type=str, required=True, help="The AAS for the gateway (hint: URI)"
    )
    parser.add_argument(
        '--aas-registry', '-a', type=str, required=False, help="The AAS registry to use", default="http://aas-registry:8080"
    )
    parser.add_argument(
        '--submodel-registry', '-s', type=str, required=False, help="The Submodel registry to use", default="http://sm-registry:8080"
    )
    parser.add_argument(
        '--gateway-config', '-c', type=str, required=False, help="The folder used by the Thingsboard gateway for configuration purposes", default="/etc/thingsboard-gateway/config"
    )
    parser.add_argument(
        '--thingsboard-host', type=str, required=False, help="Thingsboard hostname", default="localhost"
    )
    parser.add_argument(
        '--thingsboard-port', type=str, required=False, help="Thingsboard port", default="1883"
    )
    parser.add_argument(
        '--thingsboard-access-token', type=str, required=False, help="Thingsboard access token", default="1234"
    )
    # Makes the code backwards compatible with hackathon day version
    parser.add_argument(
        '--feature-assume-tsv-wrapper', type=bool, required=False, help="Assume values are wrapped in a standard {ts : <TIMESTAMP>, value: <VALUE>} json object", default=True
    )

    asyncio.run(main(parser.parse_args()))
