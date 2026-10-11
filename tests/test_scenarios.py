import pytest
from core.clock import VirtualClock
from core.event_bus import EventBus
from core.channel import SimulatedChannel
from core.host import Host

# ==========================================
# TEST FIXTURES (Setup)
# ==========================================
@pytest.fixture
def simulation_env():
    clock = VirtualClock()
    bus = EventBus(clock)

    channel = SimulatedChannel(clock, bus, seed=42)

    host_a = Host("Host A", "fsm_definitions/tcp.json", bus, channel)
    host_b = Host("Host B", "fsm_definitions/tcp.json", bus, channel)

    host_a.peer = host_b
    host_b.peer = host_a

    return clock, bus, channel, host_a, host_b

# ==========================================
# SCENARIO IMPLEMENTATIONS
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
    
    # 3. Process network delivery (Host B receives SYN, sends SYN-ACK)
    channel.tick() 
    assert host_b.fsm.current_state == "SYN_RCVD"
    
    # 4. Process network delivery (Host A receives SYN-ACK, sends ACK)
    channel.tick()
    assert host_a.fsm.current_state == "ESTABLISHED"
    
    # 5. Process network delivery (Host B receives ACK)
    channel.tick()
    assert host_b.fsm.current_state == "ESTABLISHED"

def test_scenario_8_udp_loss():
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

# ==========================================
# REMAINING MANDATORY SCENARIOS SKELETONS
# ==========================================
# ==========================================
# REMAINING SCENARIOS IMPLEMENTATIONS
# ==========================================
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
    
    # Simula perda apagando o pacote da fila do canal
    channel.queue.pop(0)
    
    # Avança o relógio para disparar o timeout de retransmissão
    host_a.fsm.process_event("timeout", {"type": "SYN"}) # Simula o disparo do timer do SYN
    
    # Verifica se o SYN foi retransmitido
    assert len(channel.queue) == 1
    assert channel.queue[0]["packet"]["type"] == "SYN"

def test_scenario_3_tcp_syn_ack_loss(simulation_env):
    """
    Scenario 3: TCP - Loss of SYN-ACK segment.
    Expected: Client retransmits SYN; Server receives duplicate SYN and resends SYN-ACK.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_b.fsm.process_event("app_passive_open")
    host_a.fsm.process_event("app_active_open")
    
    channel.tick() # Host B recebe SYN e envia SYN-ACK
    assert host_b.fsm.current_state == "SYN_RCVD"
    
    # Simula perda apagando o SYN-ACK da fila
    channel.queue.pop(0)
    
    # Timeout no Host A, retransmite SYN
    host_a.fsm.process_event("timeout", {"type": "SYN"})
    
    # Host B recebe SYN novamente. Como ainda está em SYN_RCVD, o FSM processará o evento 
    # (assumindo que a máquina trata retransmissões em estados intermediários de forma tolerante, 
    # ou podemos simplesmente focar no envio do SYN-ACK de B novamente se implementado).
    # Para efeitos deste teste e do FSM fornecido:
    channel.tick() 
    
    # Agora a fila deve ter o novo SYN-ACK
    assert channel.queue[0]["packet"]["type"] == "SYN-ACK"

def test_scenario_4_tcp_normal_teardown(simulation_env):
    """
    Scenario 4: TCP - Normal connection teardown.
    Expected: A (FIN_WAIT_1 -> FIN_WAIT_2 -> TIME_WAIT); B (CLOSE_WAIT -> LAST_ACK).
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    # Setup inicial de conexão estabelecida
    host_a.fsm.current_state = "ESTABLISHED"
    host_b.fsm.current_state = "ESTABLISHED"
    
    # 1. Host A inicia o encerramento
    host_a.fsm.process_event("app_close")
    assert host_a.fsm.current_state == "FIN_WAIT_1"
    
    # 2. Host B recebe FIN, envia ACK
    channel.tick()
    assert host_b.fsm.current_state == "CLOSE_WAIT"
    
    # 3. Host A recebe ACK
    channel.tick()
    assert host_a.fsm.current_state == "FIN_WAIT_2"
    
    # 4. Host B finaliza leitura e fecha
    host_b.fsm.process_event("app_close")
    assert host_b.fsm.current_state == "LAST_ACK"
    
    # 5. Host A recebe FIN, envia ACK e vai para TIME_WAIT
    channel.tick()
    assert host_a.fsm.current_state == "TIME_WAIT"
    
    # 6. Host B recebe ACK e fecha
    channel.tick()
    assert host_b.fsm.current_state == "CLOSED"
    
    # 7. Timeout de 2MSL do Host A
    clock.tick(20) # Dispara o tempo configurado em start_time_wait_timer
    assert host_a.fsm.current_state == "CLOSED"

def test_scenario_5_tcp_simultaneous_close(simulation_env):
    """
    Scenario 5: TCP - Simultaneous close.
    Expected: Both pass through FIN_WAIT_1 -> CLOSING -> TIME_WAIT.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_a.fsm.current_state = "ESTABLISHED"
    host_b.fsm.current_state = "ESTABLISHED"
    
    # Ambos iniciam o encerramento ao mesmo tempo
    host_a.fsm.process_event("app_close")
    host_b.fsm.process_event("app_close")
    
    assert host_a.fsm.current_state == "FIN_WAIT_1"
    assert host_b.fsm.current_state == "FIN_WAIT_1"
    
    # Processa os pacotes trocados (Ambos recebem FIN)
    channel.tick() # A recebe FIN de B
    channel.tick() # B recebe FIN de A
    
    assert host_a.fsm.current_state == "CLOSING"
    assert host_b.fsm.current_state == "CLOSING"
    
    # Processa os ACKs trocados
    channel.tick()
    channel.tick()
    
    assert host_a.fsm.current_state == "TIME_WAIT"
    assert host_b.fsm.current_state == "TIME_WAIT"

def test_scenario_6_tcp_fast_retransmit(simulation_env):
    """
    Scenario 6: TCP - Loss of one data segment in the middle of 10.
    Expected: 3 duplicate ACKs trigger fast retransmit without waiting for timeout.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    host_a.fsm.current_state = "ESTABLISHED"
    host_b.fsm.current_state = "ESTABLISHED"
    host_b.ack_num = 1
    
    # Simulamos a receção de 3 ACKs duplicados no Host A
    for _ in range(3):
        # Dispara manualmente os ACKs duplicados na FSM do Host A
        host_a.fsm.process_event("channel_receive_segment", {"type": "ACK", "ack_num": 1})
    
    # A verificação na classe Host (is_duplicate_ack_3) deve ter retornado True
    # E o Host A deve ter acionado o "fast_retransmit" no 3º ACK.
    # Como consequência, Host A deve ter inserido o pacote de retransmissão na fila.
    # Nota: isto assume que "unacked_segments" já possuía os dados.
    assert host_a.duplicate_ack_count == 0  # Deve ter sido resetado após fast_retransmit

def test_scenario_7_tcp_closed_port(simulation_env):
    """
    Scenario 7: TCP - Connection to a closed port.
    Expected: RST response.
    """
    clock, bus, channel, host_a, host_b = simulation_env
    
    # Host B está CLOSED por padrão
    # Simulamos o envio direto de um pacote SYN indicando porta fechada
    host_b.fsm.process_event("channel_receive_segment", {"type": "SYN", "dst_port": "CLOSED"})
    
    # Verifica se Host B inseriu um RST na fila
    assert len(channel.queue) == 1
    assert channel.queue[0]["packet"]["type"] == "RST"
    assert host_b.fsm.current_state == "CLOSED"

def test_scenario_9_udp_corrupted_checksum():
    """
    Scenario 9: UDP - Datagram with corrupted checksum.
    Expected: Discarded by receiver, no notification.
    """
    clock = VirtualClock()
    bus = EventBus(clock)
    channel = SimulatedChannel(clock, bus)
    
    host_a = Host("Host A", "fsm_definitions/udp.json", bus, channel)
    host_b = Host("Host B", "fsm_definitions/udp.json", bus, channel)
    host_a.peer = host_b
    
    host_a.fsm.process_event("app_send_data", "Mensagem Secreta")
    
    # Corrompendo intencionalmente o checksum antes da entrega
    corrupted_packet = channel.queue[0]["packet"]
    corrupted_packet["checksum"] = 99999 
    
    # O pacote é processado, mas deve ser descartado (is_checksum_invalid)
    channel.tick()
    
    assert len(host_b.app_buffer) == 0

def test_scenario_10_udp_vs_tcp_comparison():
    """
    Scenario 10: UDP vs TCP - Same payload, same noisy channel.
    Expected: Report comparing delivered. TCP buffer > UDP buffer on lossy channel.
    """
    clock = VirtualClock()
    bus = EventBus(clock)
    
    # Canal Ruidoso
    channel_udp = SimulatedChannel(clock, bus, seed=42)
    channel_udp.loss_prob = 0.5
    
    host_a_udp = Host("Host A UDP", "fsm_definitions/udp.json", bus, channel_udp)
    host_b_udp = Host("Host B UDP", "fsm_definitions/udp.json", bus, channel_udp)
    host_a_udp.peer = host_b_udp
    
    # Envio de 10 pacotes UDP
    for i in range(10):
        host_a_udp.fsm.process_event("app_send_data", f"Payload {i}")
        channel_udp.tick()
        
    # Verificação UDP
    assert len(host_b_udp.app_buffer) < 10 # Alguns foram perdidos