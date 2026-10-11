class EventBus:
    """
    Central bus for logging FSM transitions and errors.
    Useful for future GUI table filtering and automated assertions.
    """
    def __init__(self, clock):
        self.logs = []
        self.clock = clock

    def log_transition(self, host, old_state, event, action, new_state):
        """
        Logs a successful state transition based on the project requirements.
        """
        log_entry = {
            "time": self.clock.get_time(),
            "host": host,
            "old_state": old_state,
            "event": event,
            "action": action,
            "new_state": new_state
        }
        self.logs.append(log_entry)
        print(f"[{log_entry['time']}] {host}: {old_state} --({event}/{action})--> {new_state}")

    def log_rejection(self, host, state, event, reason):
        """
        Logs an invalid event rejection.
        """
        print(f"[{self.clock.get_time()}] {host} REJECTED EVENT '{event}' in state '{state}'. Reason: {reason}")
        
    def get_logs(self):
        return self.logs