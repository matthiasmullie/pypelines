#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from typing import Iterable
from pypelines.emitter import Emitter
from pypelines.types import EmitterArgs, EmitterConfig, EventArgs, EventName, EventPayload


class LimitEmitter(Emitter):
    def get_worker_config(self, event_name: EventName, limit: EmitterConfig) -> EmitterArgs:
        return limit


    def get_events(self, limit: EmitterArgs) -> Iterable[EventArgs]:
        for index in range(0, limit):
            yield limit, index


    def get_event_payload(self, config: EmitterConfig, args: EventArgs) -> EventPayload:
        limit, index = args
        return {'limit': limit, 'index': index}
