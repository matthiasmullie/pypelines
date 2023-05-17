#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import requests
from sseclient import SSEClient
from typing import Callable, Generator, Iterable, Literal, Tuple, TypedDict
from typing_extensions import NotRequired, Required
from pypelines import expressions
from pypelines.types import EmitterConfig, EmitterTuple, EventName, EventPayload, EventTuple


SSEEmitterConfig = TypedDict('SSEEmitterConfig', {
    'stream': Required[str],
    'format': NotRequired[Literal['string', 'json']],
    'filter': Required[str],
})


def get_emitter(event_name: EventName, config: EmitterConfig) -> EmitterTuple:
    """
    Generates a list of event emitters.

    Workflows are a combination of events and jobs: when a workflow's event is triggered,
    the associated jobs will be executed in response.

    Each type of event may have their own config: cronjobs, for example, require a schedule,
    server-sent events require a stream to listen to. These details can all be defined in a
    workflow's yaml file under the event key in whatever way makes sense for the event type.

    Example:
    ```yaml
    on:                                      # start event block
      sse:                                   # event name
        stream: https://example.com/stream   # event config
        format: json                         # more event config
        filter: 'sse["var"] == "value"'      # more event config
    ```

    Events are triggered by "emitters"; i.e. the bit of code that invokes them.
    One event type may have multiple emitters. Server-sent events, for example, may be
    triggered by new messages in an event stream, but each distinct stream may require a
    separate emitter monitoring it.

    This method returns a tuple containing a callable (first value) and any arg that
    need to be passed to the callable. Every distinct tuple will be a separate worker
    and must not contain workflow-specific information; only the bare minimum required
    to emit events. There will be another opportunity to process such events in a way
    that is specific to workflows.
    """

    return get_events, event_name, config['stream']


def get_events(event_name: EventName, stream: str) -> Iterable[EventTuple]:
    """
    Executes an event emitter, emitting events.

    This will execute a single emitter entry returned by get_emitter and return/yield
    a series of events.

    This method returns a iterable of event tuples containing a callable (first value)
    and any arg that needs to be passed to the callable (e.g. event payload)
    """

    response = requests.get(
        stream,
        stream=True,
        headers={'Accept': 'text/event-stream', 'Last-Event-ID': None}
    )

    client = SSEClient(response)
    for event in client.events():
        # @todo record `event.id` some place to allow resuming after termination
        if event.event == 'message':
            yield get_payload_for_workflow, event_name, event.data


def get_payload_for_workflow(config: EmitterConfig, event_name: EventName, data: dict) -> EventPayload:
    """
    Events can carry a payload, which can then be used in a job inside expressions.
    It is possible to customize the payload (or even prevent the event from running
    a job altogether by raising an exception) based on emitter config.
    It could, for example, be useful to format the data in a certain way (i.e. parse
    json) to that it can more easily be used in expressions.

    This method received the workflow emitter config part to allow rejecting events
    (by raising an exception) or composing a custom payload specific to the workflow
    (e.g. additional processing of the event payload). Following args are the event
    payload.

    This method returns a payload that become available as variables inside jobs.
    """

    payload = data

    # load event data as json if so desired
    if 'format' in config and config['format'] == 'json':
        payload = json.loads(payload)

    # bail if the event doesn't match a workflow's criteria
    assigned_payload = expressions.assign(event_name, payload, {})
    assert 'filter' not in config or expressions.evaluate(config['filter'], assigned_payload), 'SSE filter not satisfied'

    return payload
