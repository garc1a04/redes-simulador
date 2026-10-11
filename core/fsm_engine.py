import json
import logging

class FSMEngine:
    """
    Generic Finite State Machine engine driven by data (JSON).
    It processes events, evaluates conditions, and executes actions
    based on the defined state transitions.
    """

    def __init__(self, fsm_filepath, context_delegate, event_bus, host_name="Unknown"):
        """
        Initializes the FSM Engine.
        
        :param fsm_filepath: Path to the JSON definition file.
        :param context_delegate: The object (e.g., Host instance) implementing the actions and conditions.
        :param event_bus: System object to log transitions and failures.
        :param host_name: Name of the host (e.g., 'Host A') for logging purposes.
        """
        self.context_delegate = context_delegate
        self.event_bus = event_bus
        self.host_name = host_name
        self.fsm_data = self._load_fsm(fsm_filepath)
        
        self.protocol = self.fsm_data.get("protocol", "UNKNOWN")
        self.current_state = self.fsm_data.get("initial_state", "")

    def _load_fsm(self, filepath):
        """
        Loads and parses the JSON file containing the FSM definition.
        """
        with open(filepath, 'r') as file:
            return json.load(file)

    def process_event(self, event_name, event_data=None):
        """
        Processes an incoming event. It looks for a matching transition
        in the current state based on the event name and condition.
        
        :param event_name: The name of the triggered event.
        :param event_data: Optional payload related to the event (e.g., a packet).
        """
        state_info = self.fsm_data.get("states", {}).get(self.current_state)
        
        if not state_info:
            self._log_rejection(event_name, "Current state not found in FSM definition.")
            return False

        transitions = state_info.get("transitions", [])

        for transition in transitions:
            if transition.get("event") == event_name:
                condition_name = transition.get("condition")
                
                # If there's no condition, or the condition evaluates to True
                if not condition_name or self._evaluate_condition(condition_name, event_data):
                    self._execute_transition(transition, event_data)
                    return True

        # If loop finishes without returning, the event was invalid for this state
        self._log_rejection(event_name, f"No matching transition found for event '{event_name}' in state '{self.current_state}'.")
        return False

    def _evaluate_condition(self, condition_name, event_data):
        """
        Dynamically calls the condition method on the context delegate.
        """
        if hasattr(self.context_delegate, condition_name):
            condition_method = getattr(self.context_delegate, condition_name)
            return condition_method(event_data)
   
        logging.warning(f"Condition method '{condition_name}' not implemented in delegate.")
        return False

    def _execute_transition(self, transition, event_data):
        """
        Executes the action and changes the current state.
        """
        action_name = transition.get("action")
        new_state = transition.get("next_state")
        old_state = self.current_state

        # Execute action dynamically
        if action_name and hasattr(self.context_delegate, action_name):
            action_method = getattr(self.context_delegate, action_name)
            action_method(event_data)
        elif action_name and action_name != "do_nothing":
            logging.warning(f"Action method '{action_name}' not implemented in delegate.")

        # Update state
        self.current_state = new_state

        # Log to the event bus
        if self.event_bus:
            self.event_bus.log_transition(
                host=self.host_name,
                old_state=old_state,
                event=transition.get("event"),
                action=action_name,
                new_state=new_state
            )

    def _log_rejection(self, event_name, reason):
        """
        Logs a rejected event to the event bus.
        """
        if self.event_bus:
            self.event_bus.log_rejection(
                host=self.host_name,
                state=self.current_state,
                event=event_name,
                reason=reason
            )
