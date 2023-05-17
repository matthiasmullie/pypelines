#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import time
from croniter import croniter
from datetime import datetime, timezone
from typing import Iterable, List, TypedDict
from typing_extensions import NotRequired, Required
from zoneinfo import ZoneInfo, available_timezones
from pypelines.types import EmitterConfig, EventName, EventPayload, EventTuple, EmitterTuple


ScheduleEmitterConfig = List[TypedDict('ScheduleEmitterConfigValue', {
    'cron': Required[str],
    'timezone': NotRequired[str],
})]


def get_emitter(event_name: EventName, config: EmitterConfig) -> EmitterTuple:
    for c in config:
        assert croniter.is_valid(c['cron']), f'Invalid cron: {c["cron"]}'

        timezone = c['timezone'] if 'timezone' in c else 'UTC'
        assert timezone in available_timezones(), f'Invalid timezone: {timezone}'

    return get_events,


def get_events() -> Iterable[EventTuple]:
    # current time is taken as starting point, which means we won't
    # be triggering an event until the start of the next minute
    previous_time_tuple = datetime.now(timezone.utc).timetuple()
    while True:
        now_utc = datetime.now(timezone.utc)
        time_tuple = now_utc.timetuple()
        if (
            previous_time_tuple.tm_year != time_tuple.tm_year or
            previous_time_tuple.tm_yday != time_tuple.tm_yday or
            previous_time_tuple.tm_hour != time_tuple.tm_hour or
            previous_time_tuple.tm_min != time_tuple.tm_min
        ):
            previous_time_tuple = time_tuple
            yield get_payload_for_workflow, str(now_utc)

        # could sleep for an entire minute, but because a tiny bit
        # of code needs to execute every minute, it would start to
        # drift eventually; sleeping for just 1 second will prevent
        # such drift, while adding very little overhead (the checks
        # above that need to run every second are negligible)
        time.sleep(1)


def get_payload_for_workflow(config: EmitterConfig, now_utc: str) -> EventPayload:
    for c in config:
        timezone = c['timezone'] if 'timezone' in c else 'UTC'
        now = datetime.fromisoformat(now_utc).astimezone(ZoneInfo(timezone))

        if croniter.match(c['cron'], now):
            return {
                'm': now.minute,
                'h': now.hour,
                'dom': now.timetuple().tm_mday,
                'mon': now.month,
                'dow': now.isoweekday(), # Mon = 1; Sun = 7
            }

    assert True, 'Cron not satisfied'
