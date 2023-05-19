#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from typing import Iterable, List, TypedDict
from typing_extensions import Required
from pypelines.types import EmitterConfig, EventName, EventPayload, EventTuple, EmitterTuple


LimitEmitterConfig = List[TypedDict('LimitEmitterConfigValue', {
    'limit': Required[int],
})]


def get_emitter(event_name: EventName, config: EmitterConfig) -> EmitterTuple:
    return get_events, config


def get_events(limit: int) -> Iterable[EventTuple]:
    for index in range(0, limit):
        yield get_payload_for_workflow, limit, index


def get_payload_for_workflow(config: EmitterConfig, limit: int, index: int) -> EventPayload:
    return {'limit': limit, 'index': index}
