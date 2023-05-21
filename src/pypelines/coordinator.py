#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import pickle
from typing import Dict, List, Union
from redis import Redis
from rq import Queue
from pypelines import expressions, jobs, workflows
from pypelines.emitter import Emitter
from pypelines.types import EmitterArgs, EventPayload, EventArgs, EventName, Workflow, WorkflowId


class Coordinator:
    def __init__(
            self,
            emitters: Dict[EventName, Emitter],
            redis_url: str,
            emitter_queue_args: dict = {},
            event_queue_args: dict = {},
            job_queue_args: dict = {},
            container_prune_timeout: Union[str, int] = None,
    ):
        self.__setstate__(locals())


    # Redis instance is not pickleable, so let's only expose the details required
    # to reinitialize things after unpickling
    def __getstate__(self):
        return {
            'emitters': self.emitters,
            'redis_url': self.redis_url,
            'emitter_queue_args': self.emitter_queue_args,
            'event_queue_args': self.event_queue_args,
            'job_queue_args': self.job_queue_args,
            'container_prune_timeout': self.container_prune_timeout,
        }


    def __setstate__(self, state: dict):
        self.emitters = state['emitters']
        self.redis_url = state['redis_url']
        self.redis = Redis.from_url(self.redis_url)
        self.emitter_queue_args = state['emitter_queue_args']
        self.emitter_queue = Queue('emitter', connection=self.redis, **state['emitter_queue_args'])
        self.event_queue_args = state['event_queue_args']
        self.event_queue = Queue('event', connection=self.redis, **state['event_queue_args'])
        self.job_queue_args = state['job_queue_args']
        self.job_queue = Queue('job', connection=self.redis, **state['job_queue_args'])
        self.container_prune_timeout = state['container_prune_timeout']


    def register_workflow(
            self,
            workflow_id: WorkflowId,
            workflow: Workflow,
            volumes: dict = {},
    ) -> None:
        workflows.validate(workflow)

        for event_name, event_config in workflow['on'].items():
            assert event_name in self.emitters, f'No emitter found for {event_name}'

            if event_name in self.emitters:
                emitter = self.emitters[event_name]
                emitter_args = emitter.get_worker_config(event_name, workflow['on'][event_name])
                event_emitter_key = pickle.dumps((emitter, emitter_args))

                # enqueue emitter if it doesn't already exist
                if not self.redis.exists(event_emitter_key):
                    self.emitter_queue.enqueue(
                        self.run_emitter,
                        args=(event_name, emitter, emitter_args),
                    )

                # push workflow id to emitter/workflow map if it's not already there
                workflow_ids = [workflow.decode('utf-8') for workflow in self.redis.lrange(event_emitter_key, 0, -1)]
                if not workflow_id in workflow_ids:
                    self.redis.rpush(event_emitter_key, workflow_id)

            # store workflow
            self.redis.set(workflow_id, pickle.dumps((workflow, volumes)))


    def run_emitter(
            self,
            event_name: EventName,
            emitter: Emitter,
            emitter_args: EmitterArgs,
    ) -> None:
        events = emitter.get_events(emitter_args)
        event_emitter_key = pickle.dumps((emitter, emitter_args))
        workflow_ids = [workflow.decode('utf-8') for workflow in self.redis.lrange(event_emitter_key, 0, -1)]
        for event_args in events:
            self.event_queue.enqueue(
                self.run_event,
                args=(event_name, workflow_ids, emitter, event_args),
                result_ttl=0,
                failure_ttl=0,
            )


    def run_event(
            self,
            event_name: EventName,
            workflow_ids: List[WorkflowId],
            emitter: Emitter,
            event_args: EventArgs,
    ) -> None:
        for workflow_id in workflow_ids:
            workflow_details = self.redis.get(workflow_id)
            if not workflow_details:
                continue

            workflow, volumes = pickle.loads(workflow_details)
            payload = emitter.get_event_payload(workflow['on'][event_name], event_args)
            self.job_queue.enqueue(
                self.run_jobs,
                args=(
                    workflow,
                    expressions.assign(event_name, payload, {}),
                    volumes,
                ),
                result_ttl=0,
                failure_ttl=0,
            )


    def run_jobs(
            self,
            workflow: Workflow,
            payload: EventPayload,
            volumes: dict = {},
    ) -> None:
        # cleanup before executing job
        if self.container_prune_timeout is not None:
            jobs.clean(self.container_prune_timeout)

        output = jobs.run(
            workflow['jobs'],
            payload,
            volumes,
        )
        print(output)
