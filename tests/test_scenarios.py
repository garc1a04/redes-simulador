import pytest
from core.clock import VirtualClock
from core.event_bus import EventBus
from core.channel import SimulatedChannel
from core.host import Host

# ==========================================
# SCENARIO IMPLEMENTATIONS (1 to 10)
# ========================================== 

def test_scenario_1_tcp_handshake(simulation_env):
    """
    Scenario 1: TCP - Flawless Handshake.
    Expected: A (CLOSED -> SYN_SENT -> ESTABLISHED); B (LISTEN -> SYN_RCVD -> ESTABLISHED).
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    # 1. Server (Host B) performs a passive open
    host_b.fsm.process_event("app_passive_open")
    assert host_b.fsm.current_state == "LISTEN"
    
    # 2. Client (Host A) performs an active open
    host_a.fsm.process_event("app_active_open")
    assert host_a.fsm.current_state == "SYN_SENT"
    
    # 3. Host B receives SYN, sends SYN-ACK
    channel.tick() 
    assert host_b.fsm.current_state == "SYN_RCVD"
    
    # 4. Host A receives SYN-ACK, sends ACK
    channel.tick()
    assert host_a.fsm.current_state == "ESTABLISHED"
    
    # 5. Host B receives ACK
    channel.tick()
    assert host_b.fsm.current_state == "ESTABLISHED"


def test_scenario_2_tcp_syn_loss(simulation_env):
    """
    Scenario 2: TCP - Loss of SYN segment.
    Expected: Timeout and SYN retransmission.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_b.fsm.process_event("app_passive_open")
    host_a.fsm.process_event("app_active_open")
    
    assert host_a.fsm.current_state == "SYN_SENT"
    assert len(channel.queue) == 1
    
    # Simulates loss by removing the packet from the channel queue
    channel.queue.pop(0)
    
    # Advances virtual clock by 15 ticks to trigger Host A's SYN timeout
    clock.tick(15)
    
    # Verifies SYN retransmission
    assert host_a.fsm.current_state == "SYN_SENT"
    assert len(channel.queue) >= 1
    assert channel.queue[0]["packet"]["type"] == "SYN"


def test_scenario_3_tcp_syn_ack_loss(simulation_env):
    """
    Scenario 3: TCP - Loss of SYN-ACK segment.
    Expected: Client retransmits SYN; Server receives duplicate SYN and resends SYN-ACK.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_b.fsm.process_event("app_passive_open")
    host_a.fsm.process_event("app_active_open")
    
    channel.tick()  # Host B receives SYN and sends SYN-ACK
    assert host_b.fsm.current_state == "SYN_RCVD"
    
    # Simulates loss of SYN-ACK by clearing the channel queue
    channel.queue.clear()
    
    # Timeout on Host A triggers SYN retransmission
    clock.tick(15)
    
    # Process remaining packets until handshake completes
    while channel.queue:
        channel.tick()
        
    assert host_a.fsm.current_state == "ESTABLISHED"
    assert host_b.fsm.current_state == "ESTABLISHED"


def test_scenario_4_tcp_normal_teardown(simulation_env):
    """
    Scenario 4: TCP - Normal connection teardown.
    Expected: A (FIN_WAIT_1 -> FIN_WAIT_2 -> TIME_WAIT -> CLOSED); B (CLOSE_WAIT -> LAST_ACK -> CLOSED).
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_a.fsm.current_state = "ESTABLISHED"
    host_b.fsm.current_state = "ESTABLISHED"
    
    # 1. Host A initiates active close
    host_a.fsm.process_event("app_close")
    assert host_a.fsm.current_state == "FIN_WAIT_1"
    
    # 2. Host B receives FIN, sends ACK
    channel.tick()
    assert host_b.fsm.current_state == "CLOSE_WAIT"
    
    # 3. Host A receives ACK
    channel.tick()
    assert host_a.fsm.current_state == "FIN_WAIT_2"
    
    # 4. Host B application closes
    host_b.fsm.process_event("app_close")
    assert host_b.fsm.current_state == "LAST_ACK"
    
    # 5. Host A receives FIN, sends ACK, enters TIME_WAIT
    channel.tick()
    assert host_a.fsm.current_state == "TIME_WAIT"
    
    # 6. Host B receives ACK and closes
    channel.tick()
    assert host_b.fsm.current_state == "CLOSED"
    
    # 7. 2MSL timer (20 ticks) expires on Host A
    clock.tick(20)
    assert host_a.fsm.current_state == "CLOSED"


def test_scenario_5_tcp_simultaneous_close(simulation_env):
    """
    Scenario 5: TCP - Simultaneous close.
    Expected: Both hosts pass through FIN_WAIT_1 -> CLOSING -> TIME_WAIT -> CLOSED.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_a.fsm.current_state = "ESTABLISHED"
    host_b.fsm.current_state = "ESTABLISHED"
    
    # Both hosts initiate close simultaneously
    host_a.fsm.process_event("app_close")
    host_b.fsm.process_event("app_close")
    
    assert host_a.fsm.current_state == "FIN_WAIT_1"
    assert host_b.fsm.current_state == "FIN_WAIT_1"
    
    # 1st tick: Host B receives FIN from Host A
    channel.tick()
    assert host_b.fsm.current_state == "CLOSING"
    
    # 2nd tick: Host A receives FIN from Host B
    channel.tick()
    assert host_a.fsm.current_state == "CLOSING"
    
    # 3rd tick: Host A receives ACK from Host B -> Host A enters TIME_WAIT
    channel.tick()
    assert host_a.fsm.current_state == "TIME_WAIT"
    
    # 4th tick: Host B receives ACK from Host A -> Host B enters TIME_WAIT
    channel.tick()
    assert host_b.fsm.current_state == "TIME_WAIT"
    
    # 2MSL timers expire on both hosts
    clock.tick(20)
    assert host_a.fsm.current_state == "CLOSED"
    assert host_b.fsm.current_state == "CLOSED"


def test_scenario_6_tcp_fast_retransmit(simulation_env):
    """
    Scenario 6: TCP - Loss of one data segment in the middle of data flow.
    Expected: 3 duplicate ACKs trigger fast retransmit without waiting for timeout.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_a.fsm.current_state = "ESTABLISHED"
    host_b.fsm.current_state = "ESTABLISHED"
    
    # Host A sends data segment
    host_a.fsm.process_event("app_send_data", "Segment 1")
    assert len(host_a.unacked_segments) == 1
    assert len(channel.queue) == 1
    
    # Simulate loss in channel
    channel.queue.pop(0)
    
    # Establish baseline for Host A's last_received_ack_num
    host_a.fsm.process_event("channel_receive_segment", {"type": "ACK", "ack_num": 0})
    assert host_a.last_received_ack_num == 0
    
    # Simulate 3 duplicate ACKs arriving at Host A
    host_a.fsm.process_event("channel_receive_segment", {"type": "ACK", "ack_num": 0}) # Dup 1
    host_a.fsm.process_event("channel_receive_segment", {"type": "ACK", "ack_num": 0}) # Dup 2
    host_a.fsm.process_event("channel_receive_segment", {"type": "ACK", "ack_num": 0}) # Dup 3 -> Fast Retransmit
    
    # Fast retransmit should immediately place the oldest unacked segment into the channel queue
    assert len(channel.queue) == 1
    assert channel.queue[0]["packet"]["type"] == "DATA"
    assert channel.queue[0]["packet"]["payload"] == "Segment 1"
    assert host_a.duplicate_ack_count == 0


def test_scenario_7_tcp_closed_port(simulation_env):
    """
    Scenario 7: TCP - Connection to a closed port.
    Expected: RST response.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    # Host B is in CLOSED state
    host_b.fsm.process_event("channel_receive_segment", {"type": "SYN", "dst_port": "CLOSED"})
    
    # Host B responds with RST and remains in CLOSED state
    assert len(channel.queue) == 1
    assert channel.queue[0]["packet"]["type"] == "RST"
    assert host_b.fsm.current_state == "CLOSED"


def test_scenario_8_udp_loss():
    """
    Scenario 8: UDP - 20 datagrams with 30% loss probability.
    Expected: Lost datagrams are not recovered, no retransmissions occur.
    """
    clock = VirtualClock()
    bus = EventBus(clock)
    channel = SimulatedChannel(clock, bus, seed=10)
    channel.loss_prob = 0.30

    host_a = Host("Host A", "fsm_definitions/udp.json", bus, channel)
    host_b = Host("Host B", "fsm_definitions/udp.json", bus, channel)

    host_a.peer = host_b
    host_b.peer = host_a

    for i in range(20):
        host_a.fsm.process_event("app_send_data", f"Payload {i}")

    for _ in range(100):
        channel.tick()
        clock.tick()

    received_count = len(host_b.app_buffer)
    assert received_count < 20
    assert received_count > 10

    retransmission_logs = [log for log in bus.get_logs() if log['event'] == 'timeout']
    assert len(retransmission_logs) == 0


def test_scenario_9_udp_corrupted_checksum():
    """
    Scenario 9: UDP - Datagram with corrupted checksum.
    Expected: Discarded by receiver without notification.
    """
    clock = VirtualClock()
    bus = EventBus(clock)
    channel = SimulatedChannel(clock, bus)
    
    host_a = Host("Host A", "fsm_definitions/udp.json", bus, channel)
    host_b = Host("Host B", "fsm_definitions/udp.json", bus, channel)
    host_a.peer = host_b
    host_b.peer = host_a
    
    host_a.fsm.process_event("app_send_data", "Secret Message")
    
    # Corrupt checksum before delivery
    corrupted_packet = channel.queue[0]["packet"]
    corrupted_packet["checksum"] = 99999 
    
    # Deliver packet to receiver
    channel.tick()
    
    # Packet must be silently discarded by receiver
    assert len(host_b.app_buffer) == 0


def test_scenario_10_udp_vs_tcp_comparison():
    """
    Scenario 10: UDP vs TCP - Same payload, same noisy channel.
    Expected: TCP guarantees 100% delivery via retransmissions; UDP loses datagrams.
    """
    clock = VirtualClock()
    bus = EventBus(clock)
    
    # 1. UDP Simulation on Lossy Channel (50% loss)
    channel_udp = SimulatedChannel(clock, bus, seed=42)
    channel_udp.loss_prob = 0.50
    
    host_a_udp = Host("Host A UDP", "fsm_definitions/udp.json", bus, channel_udp)
    host_b_udp = Host("Host B UDP", "fsm_definitions/udp.json", bus, channel_udp)
    host_a_udp.peer = host_b_udp
    host_b_udp.peer = host_a_udp
    
    for i in range(10):
        host_a_udp.fsm.process_event("app_send_data", f"Data {i}")
        
    for _ in range(50):
        channel_udp.tick()
        clock.tick()
        
    delivered_udp = len(host_b_udp.app_buffer)
    assert delivered_udp < 10

    # 2. TCP Simulation on Same Lossy Channel (50% loss)
    clock_tcp = VirtualClock()
    bus_tcp = EventBus(clock_tcp)
    channel_tcp = SimulatedChannel(clock_tcp, bus_tcp, seed=42)
    channel_tcp.loss_prob = 0.50
    
    host_a_tcp = Host("Host A TCP", "fsm_definitions/tcp.json", bus_tcp, channel_tcp)
    host_b_tcp = Host("Host B TCP", "fsm_definitions/tcp.json", bus_tcp, channel_tcp)
    host_a_tcp.peer = host_b_tcp
    host_b_tcp.peer = host_a_tcp
    
    # Establish connection first without loss for clean setup
    channel_tcp.loss_prob = 0.0
    host_b_tcp.fsm.process_event("app_passive_open")
    host_a_tcp.fsm.process_event("app_active_open")
    for _ in range(10):
        channel_tcp.tick()
        clock_tcp.tick()
    assert host_a_tcp.fsm.current_state == "ESTABLISHED"
    
    # Enable 50% loss for data transfer
    channel_tcp.loss_prob = 0.50
        
    # Change this to 10 to match UDP's payload size
    for i in range(10): 
        host_a_tcp.fsm.process_event("app_send_data", f"Data {i}")

    # Run simulation to allow timeouts and retransmissions
    for _ in range(12000):
        channel_tcp.tick()
        clock_tcp.tick()

    # TCP recovers lost packets, guaranteeing reliable delivery
    delivered_tcp = len(host_b_tcp.app_buffer)
    assert delivered_tcp == 10
    assert delivered_tcp > delivered_udp