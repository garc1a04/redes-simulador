from core.fsm_engine import FSMEngine
from core.utils import calculate_checksum

class Host:
    def __init__(self, name, fsm_path, bus, channel):
        self.name = name
        self.bus = bus
        self.channel = channel
        self.peer = None
        
        # Buffers e variáveis de estado
        self.app_buffer = []
        self.seq_num = 0
        self.ack_num = 0
        self.duplicate_ack_count = 0
        self.last_received_ack_num = -1
        self.unacked_segments = []
        
        # Variáveis do temporizador dinâmico RTT
        self.estimated_rtt = None
        self.dev_rtt = 0
        self.timeout_interval = 10
        
        # FSM
        self.fsm = FSMEngine(fsm_path, self, bus, host_name=name)

    # ==========================================
    # TCP - GESTÃO DE VARIÁVEIS
    # ==========================================
    def initialize_variables(self, data=None):
        self.seq_num = 0
        self.ack_num = 0
        self.duplicate_ack_count = 0
        self.last_received_ack_num = -1
        self.unacked_segments = []
        self.app_buffer = []

    # ==========================================
    # TCP - AUXILIARES DE CORRUPÇÃO E VALIDAÇÃO
    # ==========================================
    def is_corrupted(self, packet):
        if not isinstance(packet, dict):
            return True
        if packet.get("corrupted", False):
            return True
        if "checksum" in packet and "data" in packet:
            return not self.is_checksum_valid(packet)
        return False

    # ==========================================
    # TCP - CONDIÇÕES (Retornam True/False)
    # ==========================================
    def is_syn(self, packet):
        return isinstance(packet, dict) and not self.is_corrupted(packet) and packet.get("type") == "SYN"

    def is_syn_ack(self, packet):
        return isinstance(packet, dict) and not self.is_corrupted(packet) and packet.get("type") == "SYN-ACK"

    def is_ack(self, packet):
        return isinstance(packet, dict) and not self.is_corrupted(packet) and packet.get("type") == "ACK"

    def is_fin(self, packet):
        return isinstance(packet, dict) and not self.is_corrupted(packet) and packet.get("type") == "FIN"

    def is_dest_port_closed(self, packet):
        return isinstance(packet, dict) and not self.is_corrupted(packet) and packet.get("dst_port") == "CLOSED"

    def is_valid_data(self, packet):
        return isinstance(packet, dict) and not self.is_corrupted(packet) and packet.get("type") == "DATA"

    def is_new_ack(self, packet):
        if not self.is_ack(packet):
            return False
        
        ack_num = packet.get("ack_num")
        if ack_num is None:
            return False
        
        # Um novo ACK avança a sequência em relação ao último recebido
        if ack_num > self.last_received_ack_num or self.last_received_ack_num == -1:
            self.last_received_ack_num = ack_num
            self.duplicate_ack_count = 0
            return True
        return False

    def is_duplicate_ack_3(self, packet):
        if not self.is_ack(packet) or len(self.unacked_segments) == 0:
            self.duplicate_ack_count = 0
            return False

        ack_num = packet.get("ack_num")
        if ack_num is not None and ack_num == self.last_received_ack_num:
            self.duplicate_ack_count += 1
            return self.duplicate_ack_count >= 3
        return False

    # Filtros Rigorosos de Timeouts
    def is_syn_timeout(self, event_data):
        return isinstance(event_data, dict) and event_data.get("type") == "SYN_TIMEOUT"

    def is_data_timeout(self, event_data):
        return isinstance(event_data, dict) and event_data.get("type") == "DATA_TIMEOUT"

    def is_2msl_timeout(self, event_data):
        return isinstance(event_data, dict) and event_data.get("type") == "2MSL_TIMEOUT"

    def is_fin_timeout(self, event_data):
        return isinstance(event_data, dict) and event_data.get("type") == "FIN_TIMEOUT"

    # ==========================================
    # TCP - AÇÕES DE ESTADO
    # ==========================================
    def handle_syn(self, packet):
        if self.peer is None: raise ValueError("peer is required")
        # Transição de estado tratada estritamente pelo FSMEngine (JSON)
        self.ack_num = 1
        self.send_syn_ack_segment()

    def handle_syn_ack(self, packet):
        if self.peer is None: raise ValueError("peer is required")
        timer_name = f"syn_timeout_{self.name}"
        self.bus.clock.cancel_timer(timer_name)
        # Transição de estado tratada estritamente pelo FSMEngine (JSON)
        self.send_ack_segment()

    def handle_ack(self, packet):
        # Transição de estado tratada estritamente pelo FSMEngine (JSON)
        timer_name = f"syn_timeout_{self.name}"
        self.bus.clock.cancel_timer(timer_name)

    def send_syn_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "SYN", "src": self.name, "dst": self.peer.name, "seq": self.seq_num}, sender=self, receiver=self.peer)
        
        # Armar o timer específico do SYN
        timer_name = f"syn_timeout_{self.name}"
        self.bus.clock.set_timer(15, lambda: self.fsm.process_event("timeout", {"type": "SYN_TIMEOUT"}), timer_name)

    def resend_syn_segment(self, data=None):
        self.send_syn_segment()

    def send_syn_ack_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "SYN-ACK", "src": self.name, "dst": self.peer.name, "seq": self.seq_num}, sender=self, receiver=self.peer)
        
        timer_name = f"syn_timeout_{self.name}"
        self.bus.clock.set_timer(15, lambda: self.fsm.process_event("timeout", {"type": "SYN_TIMEOUT"}), timer_name)

    def send_ack_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        
        # Destruir sempre o timer do SYN ao enviar um ACK (garante o fim limpo do handshake)
        timer_name = f"syn_timeout_{self.name}"
        self.bus.clock.cancel_timer(timer_name)
        
        self.channel.send({"type": "ACK", "src": self.name, "dst": self.peer.name, "ack_num": self.ack_num}, sender=self, receiver=self.peer)

    def send_rst_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        self.channel.send({"type": "RST", "src": self.name, "dst": self.peer.name}, sender=self, receiver=self.peer)

    def send_fin_segment(self, data=None):
        if self.peer is None: 
            raise ValueError("peer is required")
        
        # Envia o pacote FIN
        self.channel.send({"type": "FIN", "src": self.name, "dst": self.peer.name, "seq": self.seq_num}, sender=self, receiver=self.peer)
        
        # Arma o temporizador de retransmissão do FIN
        timer_name = f"fin_timeout_{self.name}"
        self.bus.clock.set_timer(15, lambda: self.fsm.process_event("timeout", {"type": "FIN_TIMEOUT"}), timer_name)

    def resend_fin_segment(self, data=None):
        # Ação chamada caso ocorra timeout aguardando o ACK do FIN
        self.send_fin_segment()

    def cancel_fin_timer(self, data=None):
        timer_name = f"fin_timeout_{self.name}"
        self.bus.clock.cancel_timer(timer_name)

    def send_ack_and_start_time_wait_timer(self, data=None):
        self.send_ack_segment()
        self.start_time_wait_timer()

    def start_time_wait_timer(self, data=None):
        self.cancel_all_timers()
        timer_name = f"2msl_timeout_{self.name}"
        self.bus.clock.set_timer(20, lambda: self.fsm.process_event("timeout", {"type": "2MSL_TIMEOUT"}), timer_name)
    
    def delete_tcb(self, data=None):
        self.cancel_all_timers()
        self.initialize_variables()

    # ==========================================
    # TCP - TRANSFERÊNCIA DE DADOS (COM RTT)
    # ==========================================
    def update_rtt(self, sample_rtt):
        # Verifica se não existe OU se é None
        if getattr(self, 'estimated_rtt', None) is None:
            self.estimated_rtt = sample_rtt
            self.dev_rtt = sample_rtt / 2
        else:
            alpha = 0.125
            beta = 0.25
            self.estimated_rtt = (1 - alpha) * self.estimated_rtt + alpha * sample_rtt
            self.dev_rtt = (1 - beta) * self.dev_rtt + beta * abs(sample_rtt - self.estimated_rtt)
            
        # Calcula o intervalo com piso mínimo de 50 ticks para evitar retransmissões prematuras
        calculated_timeout = int(self.estimated_rtt + 4 * self.dev_rtt)
        self.timeout_interval = max(50, calculated_timeout)

    def send_data_segment_and_start_timer(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        
        segment = {"type": "DATA", "payload": data, "src": self.name, "dst": self.peer.name, "seq": self.seq_num}
        
        self.unacked_segments.append({
            "segment": segment,
            "send_time": self.bus.clock.get_time()
        })
        
        self.seq_num += len(data) if data else 1
        self.channel.send(segment, sender=self, receiver=self.peer)
        
        timer_name = f"data_timeout_{self.name}"
        self.bus.clock.set_timer(self.timeout_interval, lambda: self.fsm.process_event("timeout", {"type": "DATA_TIMEOUT"}), timer_name)

    def process_new_ack(self, packet):
        ack_received = packet.get("ack_num")
        if ack_received is None:
            return
        
        # Todos os segmentos com 'seq' menor que o ACK recebido foram entregues com sucesso
        acknowledged = [item for item in self.unacked_segments if item["segment"]["seq"] < ack_received]
        
        # Mantém na janela apenas os que ainda não foram confirmados
        self.unacked_segments = [item for item in self.unacked_segments if item["segment"]["seq"] >= ack_received]
        
        if acknowledged:
            self.cancel_all_timers()
            sample_rtt = self.bus.clock.get_time() - acknowledged[-1]["send_time"]
            self.update_rtt(sample_rtt)
            
            timer_name = f"data_timeout_{self.name}"
            
            # Se a janela de pacotes não confirmados não estiver vazia, reinicia o temporizador
            if self.unacked_segments:
                self.bus.clock.set_timer(self.timeout_interval, lambda: self.fsm.process_event("timeout", {"type": "DATA_TIMEOUT"}), timer_name)

    def send_cumulative_ack(self, packet=None):
        if self.peer is None: raise ValueError("peer is required")
        
        # O argumento 'packet' (passado pelo motor FSM) contém o segmento recebido
        if isinstance(packet, dict) and "seq" in packet:
            payload = packet.get("payload")
            payload_len = len(payload) if payload else 1
            
            # O ACK em TCP indica o PRÓXIMO byte/sequência que o Host espera receber
            expected_seq = packet["seq"] + payload_len
            
            # Atualiza o ack_num apenas se o pacote recebido avançar a janela
            self.ack_num = max(self.ack_num, expected_seq)
        else:
            self.ack_num += 1
            
        self.duplicate_ack_count = 0 
        self.send_ack_segment()

    def fast_retransmit(self, data=None):
        self.duplicate_ack_count = 0
        self.retransmit_oldest_unacked_segment()

    def retransmit_oldest_unacked_segment(self, data=None):
        if self.peer is None: raise ValueError("peer is required")
        if self.unacked_segments:
            oldest_item = self.unacked_segments[0]
            segment_to_send = oldest_item["segment"] if isinstance(oldest_item, dict) and "segment" in oldest_item else oldest_item
            
            self.channel.send(segment_to_send, sender=self, receiver=self.peer)

    # ==========================================
    # UDP
    # ==========================================
    def is_checksum_valid(self, packet):
        return (isinstance(packet, dict) and 
                not packet.get("corrupted", False) and 
                "checksum" in packet and 
                packet["checksum"] == calculate_checksum(packet.get("data", "")))

    def is_checksum_invalid(self, packet):
        return not self.is_checksum_valid(packet)

    def extract_and_deliver_to_app(self, packet):
        if isinstance(packet, dict) and "data" in packet:
            self.app_buffer.append(packet["data"])
        return True

    def discard_datagram_silently(self, packet):
        return True

    def create_datagram_and_send(self, data):
        if self.peer is None: raise ValueError("peer is required")

        datagram = {
            "src_port": 12345,
            "dst_port": 80,
            "length": len(data),
            "data": data,
            "checksum": calculate_checksum(data)
        }
        self.channel.send(datagram, sender=self, receiver=self.peer)

    def resend_syn_ack_segment(self, data=None):
        self.send_syn_ack_segment()

    def cancel_all_timers(self):
        timer_syn = f"syn_timeout_{self.name}"
        timer_fin = f"fin_timeout_{self.name}"
        timer_data = f"data_timeout_{self.name}"
        timer_2msl = f"2msl_timeout_{self.name}"
        
        self.bus.clock.cancel_timer(timer_syn)
        self.bus.clock.cancel_timer(timer_fin)
        self.bus.clock.cancel_timer(timer_data)
        self.bus.clock.cancel_timer(timer_2msl)