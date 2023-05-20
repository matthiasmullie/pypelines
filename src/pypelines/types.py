#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from typing import Any, Callable, Dict, Iterable, List, Tuple, TypedDict
from typing_extensions import NotRequired, Required


EventName = str
EmitterConfig = Any


Expression = str | List['Expression']


StepConfig = TypedDict('StepConfig', {
    'name': NotRequired[str],
    'run': NotRequired[Expression],
    'if': NotRequired[Expression],
})
JobConfig = TypedDict('JobConfig', {
    'runs-on': Required[str],
    'needs': NotRequired[List[str] | str],
    'steps': Required[List[StepConfig]],
})
JobsConfig = Dict[str, JobConfig]


WorkflowId = str
Workflow = TypedDict('Workflow', {
    'name': NotRequired[str],
    'on': Required[Dict[EventName, EmitterConfig]],
    'jobs': Required[JobsConfig],
})


EmitterArgs = Any
EventArgs = Any
EventPayload = Any
