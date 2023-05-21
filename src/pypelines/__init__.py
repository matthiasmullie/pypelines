#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import time
from glob import glob
from typing import List
from pypelines import workflows
from pypelines.coordinator import Coordinator
from pypelines.emitters.limit import LimitEmitter
from pypelines.emitters.schedule import ScheduleEmitter
from pypelines.emitters.sse import SSEEmitter


def get_files_since(directory_path: str, since: int, patterns: List[str] = ['*']) -> List[str]:
    paths = []
    for pattern in patterns:
        paths.extend(glob(os.path.join(directory_path, pattern)))
    return [path for path in paths if os.path.getmtime(path) > since]


if __name__ == '__main__':
    redis_url = os.getenv('REDIS')
    container_prune_timeout = os.getenv('CONTAINER_PRUNE_TIMEOUT')
    coordinator = Coordinator(
        {
            'limit': LimitEmitter(),
            'schedule': ScheduleEmitter(),
            'sse': SSEEmitter(redis_url),
        },
        redis_url,
        {'default_timeout': -1},
        {'default_timeout': '1h'},
        {'default_timeout': '1h'},
        container_prune_timeout,
    )

    # we'll have 2 types of workflows:
    # - user workflows; the plain no-frills workflows
    # - system workflows, the ones the codebase ships with, which can be used
    #   to bring in more (user) workflows by monitoring events
    # in order to be able to bring in user workflows from system workflows,
    # the latter will expose the volume where user volumes are stored, which
    # this script will then monitor for changes
    # for testing purposes, the example workflows directory will also be mounted,
    # so it can copy over those
    # user workflows will obviously not expose that volume as that would be a
    # vector for abuse
    system_workflows_directory = f'{os.getcwd()}/workflows/system'
    user_workflows_directory = f'{os.getcwd()}/workflows/user'
    example_workflows_directory = f'{os.getcwd()}/workflows/example'
    user_workflows_volumes = {}
    system_workflows_volumes = {user_workflows_directory: '/workflows', example_workflows_directory: '/workflows_example'}

    # register system workflows
    system_workflow_paths = get_files_since(system_workflows_directory, 0, ['*.yaml', '*.yml'])
    for path in system_workflow_paths:
        coordinator.register_workflow(path, workflows.load_from_file(path), system_workflows_volumes)

    # register user workflows and monitor changes
    previous_check_time = 0
    while True:
        user_workflow_paths = get_files_since(user_workflows_directory, previous_check_time, ['*.yaml', '*.yml'])
        for path in user_workflow_paths:
            try:
                coordinator.register_workflow(path, workflows.load_from_file(path), user_workflows_volumes)
            except Exception as e:
                print(f'Error registering workflow: {e}')

        previous_check_time = time.time()

        # monitor workflows every minute
        time.sleep(60)
