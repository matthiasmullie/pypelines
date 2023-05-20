#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from typing import Iterable
from pypelines.emitter import Emitter
from pypelines.types import EmitterArgs, EmitterConfig, EventArgs, EventName, EventPayload


class LimitEmitter(Emitter):
    @staticmethod
    def get_worker_config(event_name: EventName, limit: EmitterConfig) -> EmitterArgs:
        return limit


    @staticmethod
    def get_events(limit: EmitterArgs) -> Iterable[EventArgs]:
        for index in range(0, limit):
            yield limit, index


    @staticmethod
    def get_event_payload(config: EmitterConfig, args: EventArgs) -> EventPayload:
        limit, index = args
        return {'limit': limit, 'index': index}
