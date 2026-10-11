import pytest
from core.clock import VirtualClock
from core.event_bus import EventBus
from core.channel import SimulatedChannel
from core.host import Host

@pytest.fixture
def simulation_env():
    """
    Sets up a clean and isolated simulation environment for each test scenario.
    Instantiates the virtual clock, event bus, simulated channel, and two hosts.
    This fixture is automatically discovered and injected by pytest.
    """
    clock = VirtualClock()
    bus = EventBus(clock)
    
    # Initializes the channel with a fixed seed to ensure deterministic network faults
    channel = SimulatedChannel(clock, bus, seed=42)
    
    # Initializes Host A (Client) and Host B (Server) with the TCP FSM definition
    host_a = Host("Host A", "fsm_definitions/udp.json", bus, channel)
    host_b = Host("Host B", "fsm_definitions/udp.json", bus, channel)

    host_a.peer = host_b
    host_b.peer = host_a
    
    return clock, bus, channel, host_a, host_b