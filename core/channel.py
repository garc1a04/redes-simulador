import random

class SimulatedChannel:
    def __init__(self, clock, bus, seed=None):
        self.clock = clock
        self.bus = bus
        self.random = random.Random(seed)
        self.loss_prob = 0.0
        self.queue = []

    def send(self, packet, sender, receiver):
        if receiver is None:
            raise ValueError("receiver is required")

        self.queue.append({
            "sender": sender,
            "receiver": receiver,
            "packet": packet,
            "time": self.clock.get_time()
        })

    def tick(self):
        if not self.queue:
            return

        item = self.queue.pop(0)
        receiver = item["receiver"]
        packet = item["packet"]

        if self.random.random() < self.loss_prob:
            return

        if hasattr(receiver, "fsm"):
            protocol = receiver.fsm.protocol.lower()

        if protocol == "tcp":
            receiver.fsm.process_event("channel_receive_segment", packet)
        elif protocol == "udp":
            receiver.fsm.process_event("channel_receive_datagram", packet)