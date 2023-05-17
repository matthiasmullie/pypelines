#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import pickle
from typing import Dict, Iterable, List, Tuple
from typing import Any, List
from redis import Redis
from rq import SimpleWorker, Queue
from pypelines import expressions, jobs, workflows
from pypelines.types import Emitter, EmitterArgs, EventPayload, EmitterProvider, Event, EventArgs, EventName, Workflow, WorkflowId


DOCKER_PRUNE_TIMEOUT = os.getenv('DOCKER_PRUNE_TIMEOUT')

redis = Redis.from_url(os.getenv('REDIS'))
emitter_queue = Queue('emitter', connection=redis, default_timeout=-1)
event_queue = Queue('event', connection=redis, default_timeout='1h')
job_queue = Queue('job', connection=redis, default_timeout='1h')

emitter_callables: Dict[EventName, EmitterProvider] = {}


def register_emitter(event_name: EventName, workflow_to_emitter: EmitterProvider) -> None:
    assert event_name not in emitter_callables, 'Emitter for this event name already registered, unload existing first'
    emitter_callables[event_name] = workflow_to_emitter


def register_workflow(
        workflow_id: WorkflowId,
        workflow: Workflow,
):
    workflows.validate(workflow)

    for event_name, event_config in workflow['on'].items():
        assert event_name in emitter_callables, f'No emitter found for {event_name}'

        if event_name in emitter_callables:
            emitter, *emitter_args = emitter_callables[event_name](event_name, workflow['on'][event_name])
            event_emitter_key = pickle.dumps((emitter, emitter_args))

            # enqueue emitter if it doesn't already exist
            if not redis.exists(event_emitter_key):
                emitter_queue.enqueue(run_emitter, args=(event_name, emitter, emitter_args))

            # push workflow id to emitter/workflow map if it's not already there
            if not workflow_id in [workflow.decode('utf-8') for workflow in redis.lrange(event_emitter_key, 0, -1)]:
                redis.rpush(event_emitter_key, workflow_id)

        # store workflow
        redis.set(workflow_id, pickle.dumps(workflow))


def run_emitter(
        event_name: EventName,
        emitter: Emitter,
        emitter_args: EmitterArgs,
) -> None:
    try:
        events = emitter(*emitter_args)
    except Exception as e:
        print(f'Error executing emitter: {e}')
    else:
        event_emitter_key = pickle.dumps((emitter, emitter_args))
        workflow_ids = [workflow.decode('utf-8') for workflow in redis.lrange(event_emitter_key, 0, -1)]
        for event, *event_args in events:
            event_queue.enqueue(
                run_event,
                args=(event_name, workflow_ids, event, event_args),
                result_ttl=0,
                failure_ttl=0,
            )


def run_event(
        event_name: EventName,
        workflow_ids: List[WorkflowId],
        event: Event,
        event_args: EventArgs,
) -> None:
    for workflow_id in workflow_ids:
        workflow = redis.get(workflow_id)
        if not workflow:
            continue

        workflow = pickle.loads(workflow)
        try:
            payload = event(workflow['on'][event_name], *event_args)
        except Exception as e:
            print(f'Error executing event: {e}')
        else:
            job_queue.enqueue(
                run_jobs,
                args=(
                    workflow,
                    expressions.assign(event_name, payload, {}),
                ),
                result_ttl=0,
                failure_ttl=0,
            )


def run_jobs(
        workflow: Workflow,
        payload: EventPayload,
) -> None:
    try:
        output = jobs.run(workflow['jobs'], payload)
    except Exception as e:
        print(f'Error executing job: {e}')
    else:
        print(output) # @todo remove after testing

    jobs.clean(DOCKER_PRUNE_TIMEOUT)
