#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import time
from croniter import croniter
from datetime import datetime, timezone
from typing import Iterable
from zoneinfo import ZoneInfo, available_timezones
from pypelines.emitter import Emitter
from pypelines.types import EmitterArgs, EmitterConfig, EventArgs, EventName, EventPayload


class ScheduleEmitter(Emitter):
    @staticmethod
    def get_worker_config(event_name: EventName, config: EmitterConfig) -> EmitterArgs:
        for c in config:
            if 'cron' in c:
                assert croniter.is_valid(c['cron']), f'Invalid cron: {c["cron"]}'

            if 'iso' in c:
                datetime.fromisoformat(c['iso'])

            timezone = c['timezone'] if 'timezone' in c else 'UTC'
            assert timezone in available_timezones(), f'Invalid timezone: {timezone}'

        return None


    @staticmethod
    def get_events(args: EmitterArgs) -> Iterable[EventArgs]:
        # current time is taken as starting point, which means we won't
        # be triggering an event until the start of the next minute
        previous_time_tuple = datetime.now(timezone.utc).timetuple()
        while True:
            now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            time_tuple = now_utc.timetuple()
            if (
                    previous_time_tuple.tm_year != time_tuple.tm_year or
                    previous_time_tuple.tm_yday != time_tuple.tm_yday or
                    previous_time_tuple.tm_hour != time_tuple.tm_hour or
                    previous_time_tuple.tm_min != time_tuple.tm_min
            ):
                previous_time_tuple = time_tuple
                yield now_utc.isoformat()

            # could sleep for an entire minute, but because a tiny bit
            # of code needs to execute every minute, it would start to
            # drift eventually; sleeping for just 1 second will prevent
            # such drift, while adding very little overhead (the checks
            # above that need to run every second are negligible)
            time.sleep(1)


    @staticmethod
    def get_event_payload(config: EmitterConfig, isoformat: EventArgs) -> EventPayload:
        now_utc = datetime.fromisoformat(isoformat)

        for c in config:
            timezone = c['timezone'] if 'timezone' in c else 'UTC'
            now = now_utc.astimezone(ZoneInfo(timezone))

            payload = {
                'iso': now.isoformat(),
                'm': now.minute,
                'h': now.hour,
                'dom': now.timetuple().tm_mday,
                'mon': now.month,
                'dow': now.isoweekday(), # Mon = 1; Sun = 7
            }

            if 'cron' in c and croniter.match(c['cron'], now):
                return payload

            if 'iso' in c:
                input = datetime.fromisoformat(c['iso']).replace(second=0, microsecond=0)
                if not input.tzinfo or 'timezone' in c:
                    input = input.replace(tzinfo=ZoneInfo(timezone))
                if input == now:
                    return payload

        assert False, 'Schedule not satisfied'
