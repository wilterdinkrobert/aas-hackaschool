from dataclasses import dataclass
from enum import Enum
from typing import List


@dataclass(frozen=True)
class Timeseries:
    type: str
    key: str
    value: str = "[:]"


@dataclass(frozen=True)
class MQTTTopic:
    topic_filter: str
    timeseries: List[Timeseries]
    device_name_expr: str
    device_type_expr: str = 'default'


@dataclass(frozen=True)
class MQTT:
    host: str
    port: int
    topics: List[MQTTTopic]


@dataclass(frozen=True)
class Connector:
    type: str
    name: str
    connector: MQTT


@dataclass(frozen=True)
class Gateway:
    host: str
    port: int
    access_token: str
    connectors: List[Connector]