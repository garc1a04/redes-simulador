import random
import copy

class SimulatedChannel:
    def __init__(self, clock, bus, seed=None):
        self.clock = clock
        self.bus = bus
        self.random = random.Random(seed)
        
        # Parâmetros exigidos na secção 4.5
        self.loss_prob = 0.0
        self.corrupt_prob = 0.0
        self.duplicate_prob = 0.0
        self.reorder_prob = 0.0
        self.delay_min = 0  
        self.delay_max = 0

        self.drop_next_segment = False
        self.queue = []

    def send(self, packet, sender, receiver):
        if receiver is None:
            raise ValueError("receiver is required")

        if self.drop_next_segment:
            print(f"[Canal] Segmento {packet.get('type', '')} descartado manualmente.")
            self.drop_next_segment = False
            return

        # 1. Simulação de Perda (Loss)
        if self.random.random() < self.loss_prob:
            return  # Pacote descartado silenciosamente (não entra na fila)
        delay = self.random.randint(self.delay_min, self.delay_max)
        if self.random.random() < self.reorder_prob:
            delay += self.random.randint(self.delay_max, self.delay_max * 3)
            
        delivery_time = self.clock.get_time() + delay

        pkt_copy = copy.deepcopy(packet)
        if self.random.random() < self.corrupt_prob:
            # Estragamos propositadamente o pacote
            if "checksum" in pkt_copy:
                pkt_copy["checksum"] = ~pkt_copy["checksum"] & 0xFFFF
            else:
                pkt_copy["corrupted"] = True 

        item = {
            "sender": sender,
            "receiver": receiver,
            "packet": pkt_copy,
            "delivery_time": delivery_time
        }
        
        self.queue.append(item)
        
        if self.random.random() < self.duplicate_prob:
            dup_item = item.copy()
            dup_item["delivery_time"] += self.random.randint(1, 2)
            self.queue.append(dup_item)

        self.queue.sort(key=lambda x: x["delivery_time"])

    def tick(self):
        if self.queue and self.queue[0]["delivery_time"] <= self.clock.get_time():
            item = self.queue.pop(0)
            
            receiver = item["receiver"]
            packet = item["packet"]
            protocol = receiver.fsm.protocol.lower()

            if protocol == "tcp":
                receiver.fsm.process_event("channel_receive_segment", packet)
            elif protocol == "udp":
                receiver.fsm.process_event("channel_receive_datagram", packet)