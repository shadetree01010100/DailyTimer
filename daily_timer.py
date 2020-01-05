import logging
import sched
import threading
import time


class DailyTimer:

    """ Create a repeating, alternating 24-hour timer in only four lines:

        ```
        timer = DailyTimer(callback)
        next_on = timer.set_on(0, 0)
        next_off = timer.set_off(23, 59)
        timer.run()
        # timer.cancel()
        ```

        `callback(<True|False>)` will be called at the times scheduled
        every 24 hours. Rescheduling while running will take effect on the
        following cycle; to avoid this behavior call `cancel()`.

        Schedules are affected by local daylight savings time settings.
    """

    def __init__(self, callback):
        """ Pass a method that accepts a single boolean type argument."""
        self.logger = logging.getLogger('DailyTimer')
        self.callback = callback
        self.schedule = sched.scheduler(time.time, time.sleep)
        self.on_time = None
        self.off_time = None
        self._running = False
        self._schedule_thread = None

    def cancel(self):
        """ Clear the schedule, no further callbacks will be called until
            `run()` is called again.
        """
        for event in self.schedule.queue:
            self.schedule.cancel(event)
        self._setup()
        self.logger.info('cancelled')

    def run(self):
        """ Run the schedule in another thread.

            Raises RuntimeError if ON and OFF are not set.
        """
        # todo: handle/reschedule times in the past
        if not (self.on_time and self.off_time):
            raise RuntimeError('call set_on() and set_off() before run()')
        self._schedule_thread = threading.Thread(target=self.schedule.run)
        self._schedule_thread.start()
        self._running = True
        self.logger.info('schedule started')

    def set_off(self, hour, minute):
        """ Set time to run callback with `False` flag. If running, the
            next scheduled event will be run at its original time, and then
            rescheduled at this new time.

            Raises (TypeError, ValueError) if hour or minute is not valid.

            Returns the next time callback will be called with `False`.
        """
        return self._set_time(hour, minute, False)

    def set_on(self, hour, minute):
        """ Set time to run callback with `True` flag. If running, the
            next scheduled event will be run at its original time, and then
            rescheduled at this new time.

            Raises (TypeError, ValueError) if hour or minute is not valid.

            Returns the next time callback will be called with `True`.
        """
        return self._set_time(hour, minute, True)

    def _find_event(self, flag):
        for event in self.schedule.queue:
            if event.kwargs['flag'] == flag:
                return event

    def _reschedule(self, kwargs):
        if kwargs['flag']:
            flag = 'ON'
            hour, minute = self.on_time
        else:
            flag = 'OFF'
            hour, minute = self.off_time
        kwargs['event'] = self._tomorrow(hour, minute)
        self.schedule.enterabs(
            kwargs['event'], 1, self._run_callback, kwargs=kwargs)
        self.logger.debug('rescheduled to turn {} at {}'.format(
            flag, time.asctime(time.localtime(kwargs['event']))))

    def _run_callback(self, *args, **kwargs):
        self._reschedule(kwargs)
        self.logger.debug('running callback with {} flag'.format(
            kwargs['flag']))
        result = self.callback(kwargs['flag'])
        self.logger.debug('callback returned {}'.format(result))

    def _schedule(self, hour, minute, flag):
        previous_event = self._find_event(flag)
        if previous_event:  # has been scheduled but not run
            self.schedule.cancel(previous_event)
        event = self._today(hour, minute)
        if time.time() > self._today(hour, minute):
            event = self._tomorrow(hour, minute)
        kwargs = {'flag': flag, 'event': event}
        self.schedule.enterabs(event, 1, self._run_callback, kwargs=kwargs)
        self.logger.debug('scheduled to turn {} at {}'.format(
            'ON' if flag else 'OFF', time.asctime(time.localtime(event))))

    def _set_time(self, hour, minute, flag):
        self._validate_time(hour, minute)
        if flag:
            self.on_time = (hour, minute)
        else:
            self.off_time = (hour, minute)
        self.logger.info('{} set for {:02}:{:02}:00'.format(
            'ON' if flag else 'OFF', hour, minute))
        if self._running:
            self.logger.warning('new setting will take effect next cycle')
            return self._find_event(flag).time
        self._schedule(hour, minute, flag)
        return self._find_event(flag).time

    def _today(self, hour, minute):
        now = time.localtime()
        today = (now.tm_year, now.tm_mon, now.tm_mday,
                 hour, minute, 0,
                 now.tm_wday, now.tm_yday, now.tm_isdst)
        return time.mktime(today)

    def _tomorrow(self, hour, minute):
        return self._today(hour, minute) + 24 * 60**2

    def _validate_time(self, hour, minute):
        if not (isinstance(hour, int) and isinstance(minute, int)):
            raise TypeError('hour and minute must be type int')
        if hour not in range(24):
            raise ValueError('hour {} out of range'.format(hour))
        if minute not in range(60):
            raise ValueError('minute {} out of range'.format(minute))
