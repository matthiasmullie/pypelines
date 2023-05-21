#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import functools
import subprocess
import os
import re
from typing import List, Union
from pypelines import expressions
from pypelines.types import JobConfig, JobsConfig, StepConfig


def run(jobs: JobsConfig, data: dict, volumes: dict = {}) -> dict:
    jobs = sort_jobs(jobs)
    output = {}
    for job_name in jobs:
        job = jobs[job_name]

        dependencies = job.get('needs', [])
        dependencies = dependencies if type(dependencies) is list else [dependencies]
        for dependency in dependencies:
            assert dependency in data, 'Dependency not fulfilled'

        data = {**data}
        try:
            # capture output, and add to existing data dict for dependent jobs
            output[job_name] = data[job_name] = run_job(job_name, job, data, volumes)
        except:
            # keep trying to execute remaining jobs
            continue

    return output


def run_job(name: str, job: JobConfig, data: dict, volumes: dict = {}) -> str:
    if len(job['steps']) == 0:
        return ''

    # prepare volume args; e.g. ['-v', '/local/path:'/container/path']
    volume_binds = [f'{get_real_volume_path(src)}:{volumes[src]}' for src in volumes]
    volume_args = [val for pair in zip(['-v'] * len(volume_binds), volume_binds) for val in pair]

    # launch container
    init_output = subprocess.run(
        ['docker', 'run', '-d', '-i', *volume_args, job['runs-on']],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = init_output.stdout[:-1]

    data = {**data}
    try:
        step_output = ''
        for step in job['steps']:
            # execute step and collect output (to feed into next step)
            step_output = run_step(container_id, step, data)

            # assign output to data variables
            data = expressions.assign(name, step_output, data)

        return step_output
    finally:
        # terminate & remove container
        subprocess.run(
            ['docker', 'rm', '-f', container_id],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run_step(container_id: str, step: StepConfig, data: dict) -> str:
    assert 'if' not in step or expressions.evaluate(step['if'], data), 'Step condition not satisfied'

    if not 'run' in step:
        return ''

    # parse variables/code into command
    if type(step['run']) is list:
        command = ['docker', 'exec', '-i', container_id, *[expressions.interpolate(arg, data) for arg in step['run']]]
        shell = False
    else:
        command = f'docker exec -i {container_id} {expressions.interpolate(step["run"], data)}'
        shell = True

    # execute command on container
    output = subprocess.run(
        command,
        shell=shell,
        check=True,
        capture_output=True,
        text=True,
    )
    return output.stdout


def sort_jobs(jobs: JobsConfig) -> List[str]:
    deps_per_job = {job_name: job.get('needs', []) for job_name, job in jobs.items()}
    deps_per_job = {job_name: (deps if type(deps) is list else [deps]) for job_name, deps in deps_per_job.items()}

    def callback(x: str, y: str) -> int:
        x_deps = deps_per_job[x]
        y_deps = deps_per_job[y]

        if x in y_deps:
            return -1

        if y in x_deps:
            return 1

        return len(x_deps) - len(y_deps)

    # sort job execution order, taking dependencies into account
    sorted_job_names = sorted(jobs.keys(), key=functools.cmp_to_key(callback))
    return {job_name: jobs[job_name] for job_name in sorted_job_names}


def get_real_volume_path(volume_path: str) -> str:
    """
    When a docker container has a host volume mounted, and wants to mount that
    same volume on another container, the host path must be used rather than
    the path known in the container.

    This returns the original path on the host by looking at mounts, or the
    local path if it's not within a mount.
    """

    mounts_output = subprocess.run(
        ['cat', '/proc/self/mountinfo'],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    mounts = {dst: src for src, dst in re.findall(r'\s(/.*?)\s(/.*?)\s', mounts_output.stdout)}

    mount_path = volume_path
    while mount_path not in mounts and mount_path != '/':
        mount_path = os.path.dirname(mount_path)

    return volume_path.replace(mount_path, mounts[mount_path], 1) if mount_path in mounts else volume_path


def clean(age: Union[str, int] = '24h') -> None:
    subprocess.run(
        ['docker', 'system', 'prune', '-f', f'until={age}'],
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
