#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import jsonschema
from importlib import resources
from ruamel.yaml import YAML
from pypelines.types import Workflow


yaml=YAML(typ='safe')
schema = yaml.load(resources.open_text('schema', 'workflow.schema.yaml'))


def validate(workflow: Workflow):
    jsonschema.validate(instance=workflow, schema=schema)
