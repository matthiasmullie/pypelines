#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import requests
from sseclient import SSEClient
from typing import Iterable
from pypelines import expressions
from pypelines.emitter import Emitter
from pypelines.types import EmitterArgs, EmitterConfig, EventArgs, EventName, EventPayload


class SSEEmitter(Emitter):
    @staticmethod
    def get_worker_config(event_name: EventName, config: EmitterConfig) -> EmitterArgs:
        return event_name, config['stream']


    @staticmethod
    def get_events(args: EmitterArgs) -> Iterable[EventArgs]:
        event_name, stream = args

        response = requests.get(
            stream,
            stream=True,
            headers={'Accept': 'text/event-stream', 'Last-Event-ID': None}
        )

        client = SSEClient(response)
        for event in client.events():
            # @todo record `event.id` some place to allow resuming after termination
            if event.event == 'message':
                yield event_name, event.data


    @staticmethod
    def get_event_payload(config: EmitterConfig, args: EventArgs) -> EventPayload:
        event_name, payload = args

        # load event data as json if so desired
        if 'format' in config and config['format'] == 'json':
            payload = json.loads(payload)

        # bail if the event doesn't match a workflow's criteria
        assigned_payload = expressions.assign(event_name, payload, {})
        assert 'filter' not in config or expressions.evaluate(config['filter'], assigned_payload), 'SSE filter not satisfied'

        return payload
