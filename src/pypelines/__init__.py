#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
from ruamel.yaml import YAML
from pypelines import emitters, coordinator


yaml=YAML(typ='safe')


if __name__ == '__main__':
    coordinator.register_emitter('limit', emitters.limit.get_emitter)
    coordinator.register_emitter('schedule', emitters.schedule.get_emitter)
    coordinator.register_emitter('sse', emitters.sse.get_emitter)

    workflow_paths = (
        f'{os.getcwd()}/workflows/test/limit-test.yaml',
        f'{os.getcwd()}/workflows/test/schedule-test.yaml',
        f'{os.getcwd()}/workflows/test/sse-test.yaml',
    )
    for path in workflow_paths:
        try:
            coordinator.register_workflow(path, yaml.load(open(path, 'r')))
        except Exception as e:
            print(f'Error registering workflow: {e}')
