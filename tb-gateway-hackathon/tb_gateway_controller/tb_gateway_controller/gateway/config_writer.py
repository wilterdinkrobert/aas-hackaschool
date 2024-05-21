import dataclasses
import os
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from tb_gateway_controller.gateway.models import Gateway, Connector


class ConfigWriter:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(os.path.dirname(__file__) + "/templates/"),
            autoescape=select_autoescape()
        )

    def _render(self, jinja_template: Template, context: dict, output_file: str):
        rendered = jinja_template.render(context)
        with open(output_file, mode="w", encoding="utf-8") as fp:
            fp.write(rendered)

    def write_gateway(self, output_dir: str, gateway: Gateway) -> None:
        jinja_template = self.env.get_template('tb_gateway.json.template')
        self._render(jinja_template, dataclasses.asdict(gateway), output_dir + '/tb_gateway.json')

    def write_connectors(self, output_dir: str, connectors: List[Connector]) -> None:
        jinja_mqtt_template = self.env.get_template('tb_gateway_mqtt.json.template')
        for connector in connectors:
            if connector.type == "mqtt":
                self._render(jinja_mqtt_template, dataclasses.asdict(connector), output_dir + '/mqtt_' + connector.name + ".json")
            else:
                raise NotImplementedError(f"Connector type {connector.type} not implemented!")
