Create a repeating, alternating 24-hour timer in only four lines:

```
timer = DailyTimer(callback)
next_on = timer.set_on(0, 0)
next_off = timer.set_off(23, 59)
timer.run()
# timer.cancel()
``` 

`callback(<True|False>)` will be called at the times scheduled every day (affected by local daylight savings time settings). Rescheduling while running will take effect on the following cycle; to avoid this behavior call `cancel()`.
