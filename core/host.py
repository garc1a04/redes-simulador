from core.fsm_engine import FSMEngine
from core.utils import calculate_checksum

class Host:
    def __init__(self, name, fsm_path, bus, channel):
        self.name = name
        self.bus = bus
        self.channel = channel
        self.peer = None
        self.app_buffer = []
        self.seq_num = 0
        self.ack_num = 0
        self.duplicate_ack_count = 0
        self.unacked_segments = []
        self.fsm = FSMEngine(fsm_path, self, bus, host_name=name)
        self.estimated_rtt = None
        self.dev_rtt = 0
        self.timeout_interval = 10

    # TCP
    def initialize_variables(self, data=None):
        self.seq_num = 0
        self.ack_num = 0
        self.duplicate_ack_count = 0
        self.unacked_segments = []
        self.app_buffer = []

    # --- Condições TCP ---
    def is_syn(self, packet):
        return isinstance(packet, dict) and packet.get("type") == "SYN"

    def is_syn_ack(self, packet):
        return isinstance(packet, dict) and packet.get("type") == "SYN-ACK"

    def is_ack(self, packet):
        return isinstance(packet, dict) and packet.get("type") == "ACK"

    def is_fin(self, packet):
        return isinstance(packet, dict) and packet.get("type") == "FIN"

    def is_dest_port_closed(self, packet):
        return isinstance(packet, dict) and packet.get("dst_port") == "CLOSED"

    def is_valid_data(self, packet):
        return isinstance(packet, dict) and packet.get("type") == "DATA"

    def is_duplicate_ack_3(self, packet):
        if self.is_ack(packet):
            # Lógica simplificada: assume que pacotes com o mesmo ack_num são duplicados
            if packet.get("ack_num") == self.ack_num:
                self.duplicate_ack_count += 1
                return self.duplicate_ack_count >= 3
        return False

    def is_syn_timeout(self, event_data):
        return True 

    def is_data_timeout(self, event_data):
        return True

    def is_2msl_timeout(self, event_data):
        return True

    # --- Ações TCP ---
    def handle_syn(self, packet):
        if self.peer is None: raise ValueError("peer is required")
        self.fsm.current_state = "SYN_RCVD"
        self.ack_num = 1
        self.send_syn_ack_segment()

    def handle_syn_ack(self, packet):
        if self.peer is None: raise ValueError("peer is required")
        self.fsm.current_state = "ESTABLISHED"
        self.send_ack_segment()

    def handle_ack(self, packet):
        self.fsm.current_state = "ESTABLISHED"

    def send_syn_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "SYN", "src": self.name, "dst": self.peer.name, "seq": self.seq_num}, sender=self, receiver=self.peer)

    def resend_syn_segment(self, data=None):
        self.send_syn_segment()

    def send_syn_ack_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "SYN-ACK", "src": self.name, "dst": self.peer.name, "seq": self.seq_num}, sender=self, receiver=self.peer)

    def send_ack_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "ACK", "src": self.name, "dst": self.peer.name, "ack_num": self.ack_num}, sender=self, receiver=self.peer)

    def send_rst_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "RST", "src": self.name, "dst": self.peer.name}, sender=self, receiver=self.peer)

    def send_fin_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "FIN", "src": self.name, "dst": self.peer.name}, sender=self, receiver=self.peer)

    def send_data_segment_and_start_timer(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        segment = {"type": "DATA", "payload": data, "src": self.name, "dst": self.peer.name, "seq": self.seq_num}
        self.unacked_segments.append(segment)
        self.channel.send(segment, sender=self, receiver=self.peer)
        # Inicia o timer usando o clock do EventBus (ex: timeout de 10 ticks)
        self.bus.clock.set_timer(10, lambda: self.fsm.process_event("timeout"), "data_timeout")

    def send_cumulative_ack(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.ack_num += 1
        self.duplicate_ack_count = 0 # Reseta na chegada de novos dados
        self.send_ack_segment()

    def fast_retransmit(self, data=None):
        self.duplicate_ack_count = 0
        self.retransmit_oldest_unacked_segment()

    def retransmit_oldest_unacked_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        if self.unacked_segments:
            oldest_segment = self.unacked_segments[0]
            self.channel.send(oldest_segment, sender=self, receiver=self.peer)

    def send_ack_and_start_time_wait_timer(self, data=None):
        self.send_ack_segment()
        self.start_time_wait_timer()

    def start_time_wait_timer(self, data=None):
        # Inicia o timer de 2MSL (ex: 20 ticks) para transição para CLOSED
        self.bus.clock.set_timer(20, lambda: self.fsm.process_event("timeout"), "2msl_timeout")

    def delete_tcb(self, data=None):
        self.initialize_variables()

    # --- UDP ---
    def is_checksum_valid(self, packet):
        return isinstance(packet, dict) and "checksum" in packet and packet["checksum"] == calculate_checksum(packet["data"])

    def is_checksum_invalid(self, packet):
        return not self.is_checksum_valid(packet)

    def extract_and_deliver_to_app(self, packet):
        self.app_buffer.append(packet["data"])
        return True

    def discard_datagram_silently(self, packet):
        return True

    def create_datagram_and_send(self, data):
        if self.peer is None:
            raise ValueError("peer is required")

        datagram = {
            "src_port": 12345,
            "dst_port": 80,
            "length": len(data),
            "data": data,
            "checksum": calculate_checksum(data)
        }
        self.channel.send(datagram, sender=self, receiver=self.peer)
    # --- RTT e Timer Dinâmico (Requisito 4.4) ---
    def update_rtt(self, sample_rtt):
        """Calcula o RTT baseado nas fórmulas do TCP (RFC 6298 / Kurose)"""
        if self.estimated_rtt is None:
            self.estimated_rtt = sample_rtt
            self.dev_rtt = sample_rtt / 2
        else:
            alpha = 0.125
            beta = 0.25
            self.estimated_rtt = (1 - alpha) * self.estimated_rtt + alpha * sample_rtt
            self.dev_rtt = (1 - beta) * self.dev_rtt + beta * abs(sample_rtt - self.estimated_rtt)
        
        # Timeout = EstimatedRTT + 4 * DevRTT
        self.timeout_interval = max(1, int(self.estimated_rtt + 4 * self.dev_rtt))

    def send_data_segment_and_start_timer(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        
        segment = {"type": "DATA", "payload": data, "src": self.name, "dst": self.peer.name, "seq": self.seq_num}
        
        # Armazena o pacote JUNTO COM O TIMESTAMP de envio para calcular o SampleRTT
        self.unacked_segments.append({
            "segment": segment,
            "send_time": self.bus.clock.get_time()
        })
        
        self.seq_num += len(data) if data else 1
        self.channel.send(segment, sender=self, receiver=self.peer)
        
        timer_name = f"data_timeout_{self.name}"
        self.bus.clock.set_timer(self.timeout_interval, lambda: self.fsm.process_event("timeout", {"type": "DATA_TIMEOUT"}), timer_name)

    def is_new_ack(self, packet):
        return self.is_ack(packet) and not self.is_duplicate_ack_3(packet)

    def process_new_ack(self, packet):
        """Processa a chegada de um ACK, atualiza o RTT e desliza a janela"""
        ack_received = packet.get("ack_num")
        
        # Identifica pacotes que acabaram de ser confirmados
        acknowledged = [item for item in self.unacked_segments if item["segment"]["seq"] < ack_received]
        # Remove os confirmados do buffer
        self.unacked_segments = [item for item in self.unacked_segments if item["segment"]["seq"] >= ack_received]
        
        if acknowledged:
            # Pega no pacote mais recente confirmado neste ACK para medir o SampleRTT
            sample_rtt = self.bus.clock.get_time() - acknowledged[-1]["send_time"]
            self.update_rtt(sample_rtt)
            
            # Cancela o timer antigo e reinicia se ainda houver pacotes em trânsito
            timer_name = f"data_timeout_{self.name}"
            self.bus.clock.cancel_timer(timer_name)
            
            if self.unacked_segments:
                self.bus.clock.set_timer(self.timeout_interval, lambda: self.fsm.process_event("timeout", {"type": "DATA_TIMEOUT"}), timer_name)