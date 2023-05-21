#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import pickle
import requests
from redis import Redis
from sseclient import SSEClient
from typing import Iterable
from pypelines import expressions
from pypelines.emitter import Emitter
from pypelines.types import EmitterArgs, EmitterConfig, EventArgs, EventName, EventPayload


class SSEEmitter(Emitter):
    def __init__(self, redis_url: str):
        self.__setstate__(locals())


    # Redis instance is not pickleable, so let's only expose the details required
    # to reinitialize things after unpickling
    def __getstate__(self):
        return {
            'redis_url': self.redis_url,
        }


    def __setstate__(self, state: dict):
        self.redis_url = state['redis_url']
        self.redis = Redis.from_url(self.redis_url)


    def last_event_id_key(self, args: EmitterArgs):
        event_name, stream = args
        return f'{event_name}-{stream}-last-event-id'


    def get_worker_config(self, event_name: EventName, config: EmitterConfig) -> EmitterArgs:
        return event_name, config['stream']


    def get_events(self, args: EmitterArgs) -> Iterable[EventArgs]:
        event_name, stream = args
        last_event_id = self.redis.get(self.last_event_id_key(args))

        response = requests.get(
            stream,
            stream=True,
            headers={
                'Accept': 'text/event-stream',
                'Last-Event-ID': last_event_id.decode('utf-8') if last_event_id else None,
            }
        )

        client = SSEClient(response)
        for event in client.events():
            self.redis.set(self.last_event_id_key(args), event.id)
            if event.event == 'message':
                yield event_name, event.data


    def get_event_payload(self, config: EmitterConfig, args: EventArgs) -> EventPayload:
        event_name, payload = args

        # load event data as json if so desired
        if 'format' in config and config['format'] == 'json':
            payload = json.loads(payload)

        # bail if the event doesn't match a workflow's criteria
        assigned_payload = expressions.assign(event_name, payload, {})
        assert 'filter' not in config or expressions.evaluate(config['filter'], assigned_payload), 'SSE filter not satisfied'

        return payload
