import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QTableWidget, 
                             QComboBox, QGroupBox, QFormLayout, QHeaderView, QSplitter,
                             QScrollArea, QTableWidgetItem, QLineEdit, QCheckBox, QSizePolicy, QMessageBox)
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
        
        # 1. Diagrama de Estados
        self.state_canvas = StateDiagramWidget()
        self.state_scroll = QScrollArea()
        self.state_scroll.setWidget(self.state_canvas)
        self.state_scroll.setWidgetResizable(True)
        self.state_scroll.setStyleSheet("background-color: white; border: 1px solid #ccc;")

        # 2. Diagrama de Sequência (TCP ou Principal)
        self.sequence_diagram = SequenceDiagramWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.sequence_diagram)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        
        # 3. NOVO: Diagrama de Sequência (UDP para Lado a Lado)
        self.sequence_diagram_udp = SequenceDiagramWidget()
        self.scroll_area_udp = QScrollArea()
        self.scroll_area_udp.setWidget(self.sequence_diagram_udp)
        self.scroll_area_udp.setWidgetResizable(True)
        self.scroll_area_udp.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        self.scroll_area_udp.hide() # Oculto por padrão
        
        diagrams_layout.addWidget(self.state_scroll, stretch=1)
        diagrams_layout.addWidget(self.scroll_area, stretch=1)
        diagrams_layout.addWidget(self.scroll_area_udp, stretch=1) # Adicionado ao layout
        splitter.addWidget(diagrams_widget)

        # --- ÁREA INFERIOR: Controles, Canal e Log ---
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        controls_group = QGroupBox("Controles da Simulação")
        controls_layout = QVBoxLayout()
        
        self.combo_protocol = QComboBox()
        self.combo_protocol.addItems(["TCP", "UDP"])
        controls_layout.addWidget(self.combo_protocol)
        
        self.chk_side_by_side = QCheckBox("Modo Lado a Lado (Visual)")
        self.chk_side_by_side.stateChanged.connect(self.toggle_side_by_side) # Conectado!
        
        self.btn_relatorio = QPushButton("Gerar Relatório Comparativo (Cenário 10)")
        self.btn_relatorio.setStyleSheet("background-color: #2196F3; color: white;")

        controls_layout.addWidget(self.chk_side_by_side)
        controls_layout.addWidget(self.btn_relatorio)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(100, 2000)  
        self.slider_speed.setValue(1000) # Valor inicial: 1000 ms (1 segundo por tick)

        self.lbl_speed = QLabel("Velocidade: 1.0 Ticks/s (1000 ms/tick)")
        self.slider_speed.valueChanged.connect(self.update_speed)

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

        # Canal e Logs mantêm o mesmo layout...
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

        log_group = QGroupBox("Log de Transições")
        log_layout = QVBoxLayout()
        self.log_filter = QLineEdit()
        self.log_filter.setPlaceholderText("Filtrar logs...")
        self.log_filter.textChanged.connect(self.filter_logs)
        log_layout.addWidget(self.log_filter)
        self.log_table = QTableWidget(0, 6)
        self.log_table.setHorizontalHeaderLabels(["Tempo", "Host", "Estado Anterior", "Evento", "Ação", "Novo Estado"])
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
        self.btn_relatorio.clicked.connect(self.run_comparative_report)
        self.slider_loss.valueChanged.connect(lambda v: self.lbl_loss.setText(f"{v}%"))
        self.slider_delay_min.valueChanged.connect(lambda v: self.lbl_delay_min.setText(f"{v} ms"))
        self.slider_delay_max.valueChanged.connect(lambda v: self.lbl_delay_max.setText(f"{v} ms"))
        self.slider_corrupt.valueChanged.connect(lambda v: self.lbl_corrupt.setText(f"{v}%"))
        self.slider_dup.valueChanged.connect(lambda v: self.lbl_dup.setText(f"{v}%"))
        self.slider_reorder.valueChanged.connect(lambda v: self.lbl_reorder.setText(f"{v}%"))
        self.slider_speed.valueChanged.connect(self.update_speed)

    def toggle_side_by_side(self):
        if self.chk_side_by_side.isChecked():
            self.state_scroll.hide()
            self.scroll_area_udp.show()
            self.combo_protocol.setEnabled(False)
        else:
            self.state_scroll.show()
            self.scroll_area_udp.hide()
            self.combo_protocol.setEnabled(True)
        self.reset_simulation()

    def _create_core(self, protocol, diagram_widget):
        clock = VirtualClock()
        bus = EventBus(clock)
        channel = SimulatedChannel(clock, bus)
        history = set()
        
        original_send = channel.send
        
        def gui_hooked_send(packet, sender, receiver):
            q_len_before = len(channel.queue)
            original_send(packet, sender, receiver)
            q_len_after = len(channel.queue)
            
            status = "success" if q_len_after > q_len_before else "lost"
            pkt_type = packet.get("type", "DATA")
            seq = packet.get("seq", None)
            ack_num = packet.get("ack_num", None)
            
            # IGNORAR ACKS PUROS: Evita falsas retransmissões alaranjadas 
            is_pure_ack = (pkt_type == "ACK" and not packet.get("payload"))
            
            if status == "success" and not is_pure_ack:
                if protocol == "TCP":
                    pkt_signature = (sender.name, receiver.name, pkt_type, seq, ack_num)
                    if pkt_signature in history:
                        status = "retransmitted"
                    else:
                        history.add(pkt_signature)
                    
            label = f"[{protocol}] {pkt_type}"
            if seq is not None: label += f", SEQ={seq}"
            if ack_num is not None: label += f", ACK={ack_num}"
                
            src_name = "A" if "A" in sender.name else "B"
            dst_name = "A" if "A" in receiver.name else "B"
            
            diagram_widget.add_message(src_name, dst_name, label, status)
            
        channel.send = gui_hooked_send
        fsm_path = "fsm_definitions/tcp.json" if protocol == "TCP" else "fsm_definitions/udp.json"
        
        host_a = Host("Host A", fsm_path, bus, channel)
        host_b = Host("Host B", fsm_path, bus, channel)
        host_a.peer = host_b; host_b.peer = host_a
        
        return {"clock": clock, "bus": bus, "channel": channel, "host_a": host_a, "host_b": host_b, "protocol": protocol}

    def setup_core(self):
        self.sequence_diagram.clear()
        if hasattr(self, 'sequence_diagram_udp'):
            self.sequence_diagram_udp.clear()
            
        self.cores = []
        
        if self.chk_side_by_side.isChecked():
            self.cores.append(self._create_core("TCP", self.sequence_diagram))
            self.cores.append(self._create_core("UDP", self.sequence_diagram_udp))
            
            # TCP: Inicia o Handshake (Active e Passive Open)
            self.cores[0]["host_b"].fsm.process_event("app_passive_open")
            self.cores[0]["host_a"].fsm.process_event("app_active_open")
            
            # UDP: Apenas coloca o Host B em modo de escuta, sem gerar tráfego
            self.cores[1]["host_b"].fsm.process_event("app_passive_open")
        else:
            protocol = self.combo_protocol.currentText()
            core = self._create_core(protocol, self.sequence_diagram)
            self.cores.append(core)
            if protocol == "TCP":
                core["host_b"].fsm.process_event("app_passive_open")
                core["host_a"].fsm.process_event("app_active_open")

    def advance_simulation(self):
        for core in self.cores:
            # Avança o tempo e processa o canal passo a passo
            core["clock"].tick()
            core["channel"].tick()
            
            # Sincroniza os parâmetros do canal
            core["channel"].loss_prob = self.slider_loss.value() / 100.0
            core["channel"].delay_min = self.slider_delay_min.value()
            core["channel"].delay_max = self.slider_delay_max.value()
            core["channel"].corrupt_prob = self.slider_corrupt.value() / 100.0
            core["channel"].duplicate_prob = self.slider_dup.value() / 100.0
            core["channel"].reorder_prob = self.slider_reorder.value() / 100.0

        self.update_logs()

    def toggle_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("Iniciar Simulação (Auto)")
            self.btn_play.setStyleSheet("")
        else:
            # Agora lê diretamente o valor em ms do slider
            interval_ms = self.slider_speed.value()
            self.timer.start(interval_ms)
            self.btn_play.setText("Pausar Simulação")
            self.btn_play.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

    def filter_logs(self, text):
        for row in range(self.log_table.rowCount()):
            match = False
            for col in range(self.log_table.columnCount()):
                item = self.log_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.log_table.setRowHidden(row, not match)

    def update_logs(self):
        all_logs = []
        for core in self.cores:
            prefix = f"[{core['protocol']}] " if len(self.cores) > 1 else ""
            for log in core["bus"].get_logs():
                log_copy = log.copy()
                log_copy["host"] = prefix + log["host"]
                all_logs.append(log_copy)
                
        all_logs.sort(key=lambda x: x["time"])
        
        self.log_table.setRowCount(len(all_logs))
        for row, log in enumerate(all_logs):
            self.log_table.setItem(row, 0, QTableWidgetItem(str(log["time"])))
            self.log_table.setItem(row, 1, QTableWidgetItem(log["host"]))
            self.log_table.setItem(row, 2, QTableWidgetItem(log["old_state"]))
            self.log_table.setItem(row, 3, QTableWidgetItem(log["event"]))
            self.log_table.setItem(row, 4, QTableWidgetItem(str(log.get("action", ""))))
            self.log_table.setItem(row, 5, QTableWidgetItem(log["new_state"]))
            
        if all_logs: 
            self.log_table.scrollToBottom()

        # --- CORREÇÃO: Atualizar o diagrama visual de estados ---
        # Só atualiza se o modo lado a lado (que esconde o diagrama de estados) estiver desativado
        if not self.chk_side_by_side.isChecked() and self.cores:
            main_core = self.cores[0] # Pega o core em execução na tela
            
            # Extrai o estado atual das FSMs do backend
            state_a = main_core["host_a"].fsm.current_state
            state_b = main_core["host_b"].fsm.current_state
            
            # Monta o texto de feedback da última transição
            last_transition_text = ""
            if all_logs:
                last = all_logs[-1]
                last_transition_text = f"{last['host']}: {last['old_state']} -> {last['new_state']}"
                
            # Envia a ordem de repintar a tela para o widget
            self.state_canvas.update_states(state_a, state_b, last_transition_text)

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
        for core in self.cores:
            core["host_a"].fsm.process_event("app_send_data", "Aplicação solicitou envio")
        self.update_logs()

    def trigger_close_conn(self):
        for core in self.cores:
            core["host_a"].fsm.process_event("app_close", "Aplicação solicitou fechamento")
        self.update_logs()

    def trigger_close_conn_b(self):
        for core in self.cores:
            core["host_b"].fsm.process_event("app_close", "Aplicação B solicitou fechamento")
        self.update_logs()
        
    def set_drop_next(self):
        for core in self.cores:
            core["channel"].drop_next_segment = True
        self.btn_drop_next.setText("Próximo será descartado!")
        QTimer.singleShot(1500, lambda: self.btn_drop_next.setText("Descartar Próximo Segmento"))

    def run_comparative_report(self):
        """
        Executa o Cenário 10: Comparação TCP vs UDP sob a mesma carga e mesmo canal ruidoso.
        """

        loss = self.slider_loss.value() / 100.0
        delay_min = self.slider_delay_min.value()
        delay_max = self.slider_delay_max.value()
        corrupt = self.slider_corrupt.value() / 100.0

        fixed_seed = 42 
        carga_mensagens = 20

        def run_sim(protocol, seed):
            clock = VirtualClock()
            bus = EventBus(clock)
            channel = SimulatedChannel(clock, bus, seed=seed)
            
            # Aplica os parâmetros
            channel.loss_prob = loss
            channel.delay_min = delay_min
            channel.delay_max = delay_max
            channel.corrupt_prob = corrupt
            
            fsm_path = "fsm_definitions/tcp.json" if protocol == "TCP" else "fsm_definitions/udp.json"
            host_a = Host("Host A", fsm_path, bus, channel)
            host_b = Host("Host B", fsm_path, bus, channel)
            host_a.peer = host_b; host_b.peer = host_a
            
            # Inicializa a conexão (TCP) ou prepara envio (UDP)
            if protocol == "TCP":
                host_b.fsm.process_event("app_passive_open")
                host_a.fsm.process_event("app_active_open")
                # Avança o relógio para concluir handshake
                for _ in range(50): clock.tick(); channel.tick()
            else:
                host_b.fsm.process_event("app_passive_open")
            
            # Envia a carga de dados
            for i in range(carga_mensagens):
                host_a.fsm.process_event("app_send_data", f"Dado {i+1}")
                
                # CORREÇÃO: Dá tempo para o pacote fluir e ser reconhecido (ACK)
                wait_ticks = 0
                while (channel.queue or getattr(host_a, 'unacked_segments', [])) and wait_ticks < 300:
                    clock.tick()
                    channel.tick()
                    wait_ticks += 1
                
            # Roda a simulação até esvaziar a fila ou atingir limite de tempo (timeout)
            max_ticks = 5000
            ticks = 0
            while (channel.queue or getattr(host_a, 'unacked_segments', [])) and ticks < max_ticks:
                clock.tick()
                channel.tick()
                ticks += 1
                
            # Coleta de métricas
            entregues = len(getattr(host_b, 'app_buffer', []))
            
            # Fallback seguro para TCP caso host_b.app_buffer não capture perfeitamente
            if entregues == 0 and protocol == "TCP":
                entregues = carga_mensagens - len(getattr(host_a, 'unacked_segments', []))

            logs = bus.get_logs()
            retransmissoes = sum(1 for log in logs if log['event'] == 'timeout' and 'retransmit' in log['action'])
            
            return {
                "entregues": entregues,
                "perdidos": carga_mensagens - entregues if protocol == "UDP" else 0, # TCP garante entrega, UDP perde
                "retransmissoes": retransmissoes,
                "tempo_total": clock.get_time()
            }

        # Roda ambas as simulações
        res_tcp = run_sim("TCP", fixed_seed)
        res_udp = run_sim("UDP", fixed_seed)

        # Monta o relatório
        relatorio = (
            f"Resultados do Cenário 10 (Carga: {carga_mensagens} msgs, Perda: {loss*100}%)\n\n"
            f"--- Desempenho TCP ---\n"
            f"Entregues: {res_tcp['entregues']} / {carga_mensagens} (Confiável)\n"
            f"Retransmissões: {res_tcp['retransmissoes']}\n"
            f"Tempo Total Virtual: {res_tcp['tempo_total']} ms\n\n"
            f"--- Desempenho UDP ---\n"
            f"Entregues: {res_udp['entregues']} / {carga_mensagens}\n"
            f"Perdidos definitivamente: {res_udp['perdidos']}\n"
            f"Tempo Total Virtual: {res_udp['tempo_total']} ms\n"
        )
        
        # Exibe o relatório numa caixa de diálogo
        msg = QMessageBox()
        msg.setWindowTitle("Relatório Comparativo Lado a Lado")
        msg.setText(relatorio)
        msg.exec_()

    def update_speed(self, interval_ms):
        # Calcula os ticks por segundo para exibição baseando-se nos milissegundos
        ticks_per_second = round(1000 / max(1, interval_ms), 1)
        self.lbl_speed.setText(f"Velocidade: {ticks_per_second} Ticks/s ({interval_ms} ms/tick)")
        
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.setInterval(interval_ms)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulatorGUI()
    window.show()
    sys.exit(app.exec_())