#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from abc import ABC, abstractmethod
from typing import Iterable
from pypelines.types import EmitterArgs, EmitterConfig, EventArgs, EventName, EventPayload


class Emitter(ABC):
    @staticmethod
    @abstractmethod
    def get_worker_config(event_name: EventName, config: EmitterConfig) -> EmitterArgs:
        """
        Returns arguments required to run a worker to emit events for the given workflow.

        Workflows are a combination of events and jobs: when a workflow's event is triggered,
        the associated jobs will be executed in response.

        Each type of event may have their own config: schedule, for example, require a cron,
        server-sent events require a stream to listen to, etc.
        These details can all be defined in a workflow's yaml file under the event key in
        whatever way makes sense for the event type.

        Example:
        ```yaml
        on:                                      # start event block
          sse:                                   # event name
            stream: https://example.com/stream   # event config
            format: json                         # more event config
            filter: 'sse["var"] == "value"'      # more event config
        ```

        Events are triggered by emitters; i.e. the bit of code that invokes them.
        One event type/emitter may require multiple workers. Server-sent events, for example,
        may be triggered by new messages in an event stream, but each distinct stream will
        require a separate worker monitoring it.

        This method returns the args that are going to be needed to run a worker.
        Every distinct return value will be a separate worker, so the args should be as
        generic as possible, not containing workflow-specific information; only the bare
        minimum required to emit events in order to minimize the amount of workers required.

        There will be another opportunity (`get_event_payload()`) to later process such
        events in a way that is specific to workflows.
        """

        raise NotImplementedError('get_worker_config must be implemented')


    @staticmethod
    @abstractmethod
    def get_events(args: EmitterArgs) -> Iterable[EventArgs]:
        """
        Executes an event emitter.

        This will execute a single worker (per args returned by `get_worker_config()`) and
        return/yield a series of events.

        This method returns an iterable of event data, which will then be fed into
        `get_event_payload()` to allow for workflow-specific customization of the data
        (or rejection of the event if not relevant for that specific workflow) before that
        workflow's jobs will be executed.
        """

        raise NotImplementedError('get_events must be implemented')


    @staticmethod
    def get_event_payload(config: EmitterConfig, args: EventArgs) -> EventPayload:
        """
        Events can carry a payload, which can then be used in a job inside expressions.
        It is possible to customize the payload (or even prevent the event from running
        a job altogether by raising an exception) based on workflow emitter config.
        It could, for example, be useful to format the data in a certain way (i.e. parse
        json) to that it can more easily be used in expressions.

        This method received the workflow emitter config part to allow rejecting events
        (by raising an exception) or composing a custom payload specific to the workflow
        (e.g. additional processing of the event payload). Following args are the event
        payload.

        This method returns a payload that become available as variables within jobs.
        """

        return args
