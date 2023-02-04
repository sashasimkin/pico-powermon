from machine import Timer, reset


class WatchdogTimer:

    def __init__(self, timeout=60000, resolution=1000):
        self._timeout = timeout
        self._resolution = resolution
        self.feed()
        self._timer = Timer(period=resolution, mode=Timer.PERIODIC, callback=self._check_timeout)
    
    def feed(self):
        self._timeout_elapsed = self._timeout
    
    def _check_timeout(self, timer):
        self._timeout_elapsed -= self._resolution
        if self._timeout_elapsed <= 0:
            print("Watchdog timeout elapsed. Resetting board")
            reset()
