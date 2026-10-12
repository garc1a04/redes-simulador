import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QTableWidget, 
                             QComboBox, QGroupBox, QFormLayout, QHeaderView, QSplitter,
                             QScrollArea, QTableWidgetItem, QLineEdit, QCheckBox, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer

from core.host import Host
from core.clock import VirtualClock
from core.event_bus import EventBus
from core.channel import SimulatedChannel
from interface.diagram import SequenceDiagramWidget
from interface.state_diagram import StateDiagramWidget

class SimulatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador de Redes - TCP/UDP")
        
        # Permite redimensionar, maximizar e minimizar livremente
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)
        
        self.init_ui()
        self.setup_core()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # --- ÁREA SUPERIOR: Diagramas ---
        diagrams_widget = QWidget()
        diagrams_layout = QHBoxLayout(diagrams_widget)
        
        # 1. Diagrama de Estados com Rolagem Responsiva
        self.state_canvas = StateDiagramWidget()
        self.state_scroll = QScrollArea()
        self.state_scroll.setWidget(self.state_canvas)
        self.state_scroll.setWidgetResizable(True)
        self.state_scroll.setStyleSheet("background-color: white; border: 1px solid #ccc;")

        # 2. Diagrama de Sequência com Rolagem Responsiva
        self.sequence_diagram = SequenceDiagramWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.sequence_diagram)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        
        diagrams_layout.addWidget(self.state_scroll, stretch=1)
        diagrams_layout.addWidget(self.scroll_area, stretch=1)
        splitter.addWidget(diagrams_widget)

        # --- ÁREA INFERIOR: Controles, Canal e Log ---
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        # 1. Painel de Controles
        controls_group = QGroupBox("Controles da Simulação")
        controls_layout = QVBoxLayout()
        
        self.combo_protocol = QComboBox()
        self.combo_protocol.addItems(["TCP", "UDP"])
        controls_layout.addWidget(self.combo_protocol)
        
        self.chk_side_by_side = QCheckBox("Comparação Lado a Lado (TCP vs UDP)")
        controls_layout.addWidget(self.chk_side_by_side)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(50, 3000)
        self.slider_speed.setValue(1500)
        self.lbl_speed = QLabel("Velocidade: 1.5s")
        self.slider_speed.valueChanged.connect(lambda v: self.lbl_speed.setText(f"Velocidade: {v/1000:.1f}s"))
        controls_layout.addWidget(QLabel("Velocidade de Execução:"))
        controls_layout.addWidget(self.slider_speed)
        controls_layout.addWidget(self.lbl_speed)
        
        self.btn_step = QPushButton("Passo a Passo (Tick)")
        self.btn_send_data = QPushButton("Host A: Enviar Dados")
        self.btn_send_data.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.btn_close_conn = QPushButton("Host A: Encerrar Conexão (FIN)")
        self.btn_close_conn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")

        self.btn_close_conn_b = QPushButton("Host B: Encerrar Conexão (FIN)")
        self.btn_close_conn_b.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold;")

        self.btn_play = QPushButton("Iniciar Simulação (Auto)")
        self.btn_reset = QPushButton("Resetar")

        controls_layout.addWidget(self.btn_step)
        controls_layout.addWidget(self.btn_send_data)
        controls_layout.addWidget(self.btn_close_conn)
        controls_layout.addWidget(self.btn_close_conn_b)
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_reset)
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)

        # 2. Painel do Canal
        channel_group = QGroupBox("Parâmetros do Canal")
        channel_layout = QFormLayout()
        
        self.slider_loss = QSlider(Qt.Horizontal); self.slider_loss.setRange(0, 100); self.lbl_loss = QLabel("0%")
        self.slider_delay_min = QSlider(Qt.Horizontal); self.slider_delay_min.setRange(0, 500); self.lbl_delay_min = QLabel("0 ms")
        self.slider_delay_max = QSlider(Qt.Horizontal); self.slider_delay_max.setRange(0, 500); self.lbl_delay_max = QLabel("0 ms")
        self.slider_corrupt = QSlider(Qt.Horizontal); self.slider_corrupt.setRange(0, 100); self.lbl_corrupt = QLabel("0%")
        self.slider_dup = QSlider(Qt.Horizontal); self.slider_dup.setRange(0, 100); self.lbl_dup = QLabel("0%")
        self.slider_reorder = QSlider(Qt.Horizontal); self.slider_reorder.setRange(0, 100); self.lbl_reorder = QLabel("0%")
        
        channel_layout.addRow("Prob. Perda:", self.slider_loss); channel_layout.addRow("", self.lbl_loss)
        channel_layout.addRow("Atraso Mín (ms):", self.slider_delay_min); channel_layout.addRow("", self.lbl_delay_min)
        channel_layout.addRow("Atraso Máx (ms):", self.slider_delay_max); channel_layout.addRow("", self.lbl_delay_max)
        channel_layout.addRow("Prob. Corrupção:", self.slider_corrupt); channel_layout.addRow("", self.lbl_corrupt)
        channel_layout.addRow("Prob. Duplicação:", self.slider_dup); channel_layout.addRow("", self.lbl_dup)
        channel_layout.addRow("Prob. Reordenação:", self.slider_reorder); channel_layout.addRow("", self.lbl_reorder)
        
        self.btn_drop_next = QPushButton("Descartar Próximo Segmento")
        self.btn_drop_next.setStyleSheet("background-color: #f44336; color: white;")
        self.btn_drop_next.clicked.connect(self.set_drop_next)
        channel_layout.addRow(self.btn_drop_next)
        channel_group.setLayout(channel_layout)

        # 3. Log
        log_group = QGroupBox("Log de Transições")
        log_layout = QVBoxLayout()
        
        self.log_filter = QLineEdit()
        self.log_filter.setPlaceholderText("Filtrar logs (ex: SYN, A, CLOSED)...")
        self.log_filter.textChanged.connect(self.filter_logs)
        log_layout.addWidget(self.log_filter)

        self.log_table = QTableWidget(0, 5)
        self.log_table.setHorizontalHeaderLabels(["Tempo", "Host", "Estado Anterior", "Evento", "Novo Estado"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        log_layout.addWidget(self.log_table)
        log_group.setLayout(log_layout)

        bottom_layout.addWidget(controls_group, stretch=1)
        bottom_layout.addWidget(channel_group, stretch=1)
        bottom_layout.addWidget(log_group, stretch=2)
        splitter.addWidget(bottom_widget)

        # Conexões
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_simulation)
        self.btn_send_data.clicked.connect(self.trigger_send_data)
        self.btn_close_conn.clicked.connect(self.trigger_close_conn)
        self.btn_close_conn_b.clicked.connect(self.trigger_close_conn_b)
        self.btn_step.clicked.connect(self.advance_simulation)
        self.btn_play.clicked.connect(self.toggle_simulation) 
        self.btn_reset.clicked.connect(self.reset_simulation)

        self.slider_loss.valueChanged.connect(lambda v: self.lbl_loss.setText(f"{v}%"))
        self.slider_delay_min.valueChanged.connect(lambda v: self.lbl_delay_min.setText(f"{v} ms"))
        self.slider_delay_max.valueChanged.connect(lambda v: self.lbl_delay_max.setText(f"{v} ms"))
        self.slider_corrupt.valueChanged.connect(lambda v: self.lbl_corrupt.setText(f"{v}%"))
        self.slider_dup.valueChanged.connect(lambda v: self.lbl_dup.setText(f"{v}%"))
        self.slider_reorder.valueChanged.connect(lambda v: self.lbl_reorder.setText(f"{v}%"))

    def setup_core(self):
        self.clock = VirtualClock()
        self.bus = EventBus(self.clock)
        self.channel = SimulatedChannel(self.clock, self.bus)
        
        original_send = self.channel.send
        
        def gui_hooked_send(packet, sender, receiver):
            q_len_before = len(self.channel.queue)
            original_send(packet, sender, receiver)
            q_len_after = len(self.channel.queue)
            
            status = "success" if q_len_after > q_len_before else "lost"
            
            label = packet.get("type", "UDP DATA")
            if "seq" in packet:
                label += f", SEQ={packet['seq']}"
            if "ack_num" in packet:
                label += f", ACK={packet['ack_num']}"
                
            src_name = "A" if "A" in sender.name else "B"
            dst_name = "A" if "A" in receiver.name else "B"
            
            self.sequence_diagram.add_message(src_name, dst_name, label, status)
            
        self.channel.send = gui_hooked_send

        protocol_file = "fsm_definitions/tcp.json" if "TCP" in self.combo_protocol.currentText() else "fsm_definitions/udp.json"
        
        self.host_a = Host("Host A", protocol_file, self.bus, self.channel)
        self.host_b = Host("Host B", protocol_file, self.bus, self.channel)
        
        self.host_a.peer = self.host_b
        self.host_b.peer = self.host_a

        self.channel.loss_prob = self.slider_loss.value() / 100.0
        self.channel.delay_min = self.slider_delay_min.value()
        self.channel.delay_max = self.slider_delay_max.value()
        self.channel.corrupt_prob = self.slider_corrupt.value() / 100.0
        self.channel.duplicate_prob = self.slider_dup.value() / 100.0
        self.channel.reorder_prob = self.slider_reorder.value() / 100.0

        if "TCP" in self.combo_protocol.currentText():
            self.host_b.fsm.process_event("app_passive_open")
            self.host_a.fsm.process_event("app_active_open")
        else:
            self.bus.clock.set_timer(5, lambda: self.host_a.fsm.process_event("app_send_data", "Pacote UDP Automático"), "udp_start")

    def toggle_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("Iniciar Simulação (Auto)")
            self.btn_play.setStyleSheet("")
        else:
            speed = self.slider_speed.value()
            self.timer.start(speed) 
            self.btn_play.setText("Pausar Simulação")
            self.btn_play.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

    def set_drop_next(self):
        self.channel.drop_next_segment = True
        self.btn_drop_next.setText("Próximo será descartado!")
        QTimer.singleShot(1500, lambda: self.btn_drop_next.setText("Descartar Próximo Segmento"))

    def filter_logs(self, text):
        for row in range(self.log_table.rowCount()):
            match = False
            for col in range(self.log_table.columnCount()):
                item = self.log_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.log_table.setRowHidden(row, not match)

    def advance_simulation(self):
        initial_logs = len(self.bus.get_logs())
        initial_msgs = len(self.sequence_diagram.messages)
        
        for _ in range(100):
            self.clock.tick()
            self.channel.tick()
            
            self.channel.loss_prob = self.slider_loss.value() / 100.0
            self.channel.delay_min = self.slider_delay_min.value()
            self.channel.delay_max = self.slider_delay_max.value()
            self.channel.corrupt_prob = self.slider_corrupt.value() / 100.0
            self.channel.duplicate_prob = self.slider_dup.value() / 100.0
            self.channel.reorder_prob = self.slider_reorder.value() / 100.0

            current_logs = len(self.bus.get_logs())
            current_msgs = len(self.sequence_diagram.messages)
            
            if current_msgs > initial_msgs or current_logs > initial_logs:
                break

        self.update_logs()

    def update_logs(self):
        logs = self.bus.get_logs()
        
        last_trans_str = ""
        if logs:
            last_log = logs[-1]
            last_trans_str = f"{last_log['host']}: {last_log['event']} -> {last_log['new_state']}"

        if hasattr(self, 'host_a') and hasattr(self, 'host_b'):
            self.state_canvas.update_states(self.host_a.fsm.current_state, self.host_b.fsm.current_state, last_trans_str)

        self.log_table.setRowCount(len(logs))
        
        for row, log in enumerate(logs):
            self.log_table.setItem(row, 0, QTableWidgetItem(str(log["time"])))
            self.log_table.setItem(row, 1, QTableWidgetItem(log["host"]))
            self.log_table.setItem(row, 2, QTableWidgetItem(log["old_state"]))
            self.log_table.setItem(row, 3, QTableWidgetItem(log["event"]))
            self.log_table.setItem(row, 4, QTableWidgetItem(log["new_state"]))
            
        if logs:
            self.log_table.scrollToBottom()

    def reset_simulation(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("Iniciar Simulação (Auto)")
            self.btn_play.setStyleSheet("")
            
        self.sequence_diagram.clear()
        self.log_table.setRowCount(0)
        
        if hasattr(self, 'state_canvas'):
            self.state_canvas.update_states("CLOSED", "CLOSED")
            
        self.setup_core()
        self.update_logs()

    def trigger_send_data(self):
        self.host_a.fsm.process_event("app_send_data", "Aplicação solicitou envio de dados")
        self.update_logs()

    def trigger_close_conn(self):
        self.host_a.fsm.process_event("app_close", "Aplicação solicitou fechamento")
        self.update_logs()

    def trigger_close_conn_b(self):
        self.host_b.fsm.process_event("app_close", "Aplicação B solicitou fechamento")
        self.update_logs()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulatorGUI()
    window.show()
    sys.exit(app.exec_())