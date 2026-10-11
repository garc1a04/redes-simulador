class VirtualClock:
    """
    Virtual clock to ensure that simulation timers do not depend on real time,
    allowing for deterministic execution and instantaneous automated tests.
    """

    def __init__(self):
        """
        Initializes the virtual time at zero and creates an empty list for timers.
        """
        self.current_time = 0
        self.timers = []

    def get_time(self):
        """
        Returns the current virtual time.
        """
        return self.current_time

    def tick(self, increment=1):
        """
        Advances the virtual clock by a specific increment and triggers expired timers.
        
        :param increment: Amount of virtual time units (e.g., milliseconds) to advance.
        """
        self.current_time += increment
        self._check_timers()

    def set_timer(self, delay, callback, name="unnamed_timer"):
        """
        Schedules a callback function to be executed after a given delay in virtual time.
        
        :param delay: Virtual time units to wait before triggering.
        :param callback: Function to execute when the timer expires.
        :param name: String identifier for debugging purposes.
        """
        expiration_time = self.current_time + delay
        self.timers.append((expiration_time, callback, name))
        
        # Sort timers descending by expiration time so the earliest is at the end (O(1) pop)
        self.timers.sort(key=lambda x: x[0], reverse=True)

    def cancel_timer(self, name):
        """
        Cancels a pending timer by its name. Useful when an ACK arrives before the timeout.
        """
        self.timers = [t for t in self.timers if t[2] != name]

    def _check_timers(self):
        """
        Internal method to evaluate and execute any timers that have reached or passed their expiration.
        """
        while self.timers and self.timers[-1][0] <= self.current_time:
            _, callback, _ = self.timers.pop()
            callback()