#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import functools
import subprocess
from typing import Any, Dict, List, TypedDict
from pypelines import expressions
from pypelines.types import JobConfig, JobsConfig, StepConfig


def run(jobs: JobsConfig, data: dict) -> dict:
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
            output[job_name] = data[job_name] = run_job(job_name, job, data)
        except:
            # keep trying to execute remaining jobs
            continue

    return output


def run_job(name: str, job: JobConfig, data: dict) -> str:
    # launch container
    output = subprocess.run(
        ['docker', 'run', '-d', '-i', job['runs-on']],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = output.stdout[:-1]

    data = {**data}
    try:
        for step in job['steps']:
            # execute step and collect output (to feed into next step)
            output = run_step(container_id, step, data)

            # assign output to data variables
            data = expressions.assign(name, output, data)

        return output
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


def clean(age: str = '24h') -> None:
    subprocess.run(
        ['docker', 'system', 'prune', '-f', f'until={age}'],
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
