import math
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPolygonF, QFontMetrics
from PyQt5.QtCore import Qt, QPointF

class StateDiagramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.state_a = "CLOSED"
        self.state_b = "CLOSED"
        self.last_transition = "Nenhuma transição ainda"

        # Permite que a área do diagrama reduza ou expanda conforme a janela
        self.setMinimumWidth(320)
        self.setMinimumHeight(680)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Mapeamento com espaçamento vertical correto para evitar colisão com o cabeçalho
        self.state_positions = {
            "CLOSED": (0.50, 0.14),
            "WAIT_FOR_DATA": (0.50, 0.26), # UDP
            "SYN_SENT": (0.22, 0.26),      # Handshake Cliente
            "LISTEN": (0.78, 0.26),        # Handshake Servidor
            "SYN_RCVD": (0.78, 0.39),      # Handshake Servidor
            "ESTABLISHED": (0.50, 0.49),   # Conexão Ativa
            "FIN_WAIT_1": (0.22, 0.62),   # Encerramento Cliente
            "CLOSE_WAIT": (0.78, 0.62),   # Encerramento Servidor
            "FIN_WAIT_2": (0.22, 0.75),   # Encerramento Cliente
            "CLOSING": (0.50, 0.75),      # Fechamento Simultâneo
            "LAST_ACK": (0.78, 0.75),     # Encerramento Servidor
            "TIME_WAIT": (0.35, 0.89)     # Temporizador 2MSL
        }

        # Fluxos de transição da FSM
        self.transitions = [
            ("CLOSED", "SYN_SENT"),
            ("CLOSED", "LISTEN"),
            ("CLOSED", "WAIT_FOR_DATA"),
            ("LISTEN", "SYN_RCVD"),
            ("SYN_SENT", "ESTABLISHED"),
            ("SYN_RCVD", "ESTABLISHED"),
            ("ESTABLISHED", "FIN_WAIT_1"),
            ("ESTABLISHED", "CLOSE_WAIT"),
            ("FIN_WAIT_1", "FIN_WAIT_2"),
            ("FIN_WAIT_1", "CLOSING"),
            ("FIN_WAIT_2", "TIME_WAIT"),
            ("CLOSING", "TIME_WAIT"),
            ("CLOSE_WAIT", "LAST_ACK"),
            ("LAST_ACK", "CLOSED"),
            ("TIME_WAIT", "CLOSED")
        ]

    def update_states(self, state_a, state_b, last_transition=""):
        self.state_a = state_a
        self.state_b = state_b
        if last_transition:
            self.last_transition = last_transition
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        node_radius = 25

        # Fundo do Canvas
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        # --- PAINEL DE CABEÇALHO REORGANIZADO ---
        header_height = 52
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(245, 247, 250))
        painter.drawRoundedRect(10, 8, w - 20, header_height, 6, 6)

        # Linha 1: Legendas dos Hosts à direita
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        painter.setPen(QPen(QColor(30, 136, 229)))
        painter.drawText(w - 150, 26, "● Host A")
        painter.setPen(QPen(QColor(229, 57, 53)))
        painter.drawText(w - 80, 26, "● Host B")

        # Linha 1: Título à esquerda
        painter.setPen(QPen(QColor(80, 90, 100)))
        painter.drawText(20, 26, "Estado da FSM:")

        # Linha 2: Texto da última transição (truncado se a tela for pequena)
        fm = QFontMetrics(QFont("Arial", 8))
        trans_text = f"Última Transição: {self.last_transition}"
        elided_trans = fm.elidedText(trans_text, Qt.ElideRight, w - 40)
        
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QPen(QColor(33, 33, 33)))
        painter.drawText(20, 48, elided_trans)

        # --- 1. DESENHAR LINHAS E SETAS ---
        for src_name, dst_name in self.transitions:
            if src_name in self.state_positions and dst_name in self.state_positions:
                p1 = QPointF(w * self.state_positions[src_name][0], h * self.state_positions[src_name][1])
                p2 = QPointF(w * self.state_positions[dst_name][0], h * self.state_positions[dst_name][1])
                self._draw_arrow(painter, p1, p2, node_radius)

        # --- 2. DESENHAR NÓS E INDICADORES ---
        for state_name, (rx, ry) in self.state_positions.items():
            cx = w * rx
            cy = h * ry

            is_a = (state_name == self.state_a)
            is_b = (state_name == self.state_b)

            if is_a and is_b:
                bg_color = QColor(243, 229, 245)
                border_color = QColor(142, 36, 170)
                border_width = 3
            elif is_a:
                bg_color = QColor(227, 242, 253)
                border_color = QColor(30, 136, 229)
                border_width = 3
            elif is_b:
                bg_color = QColor(255, 235, 238)
                border_color = QColor(229, 57, 53)
                border_width = 3
            else:
                bg_color = QColor(250, 250, 250)
                border_color = QColor(189, 189, 189)
                border_width = 1

            # Círculo do estado
            painter.setBrush(bg_color)
            painter.setPen(QPen(border_color, border_width))
            painter.drawEllipse(QPointF(cx, cy), node_radius, node_radius)

            # Texto do estado
            painter.setPen(QColor(33, 33, 33) if (is_a or is_b) else QColor(117, 117, 117))
            painter.setFont(QFont("Arial", 7, QFont.Bold))
            font_metrics = painter.fontMetrics()
            text_width = font_metrics.width(state_name)
            painter.drawText(int(cx - text_width / 2), int(cy + font_metrics.height() / 4), state_name)

            # Marcador A
            if is_a:
                painter.setBrush(QColor(30, 136, 229))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(cx - node_radius, cy - node_radius + 4), 9, 9)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Arial", 8, QFont.Bold))
                painter.drawText(int(cx - node_radius - 4), int(cy - node_radius + 8), "A")

            # Marcador B
            if is_b:
                painter.setBrush(QColor(229, 57, 53))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(cx + node_radius, cy - node_radius + 4), 9, 9)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Arial", 8, QFont.Bold))
                painter.drawText(int(cx + node_radius - 4), int(cy - node_radius + 8), "B")

    def _draw_arrow(self, painter, p1, p2, radius):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)

        if dist <= 2 * radius:
            return

        ux = dx / dist
        uy = dy / dist

        start_x = p1.x() + ux * radius
        start_y = p1.y() + uy * radius
        end_x = p2.x() - ux * radius
        end_y = p2.y() - uy * radius

        pen = QPen(QColor(200, 205, 210), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))

        arrow_size = 6
        angle = math.atan2(dy, dx)
        p_arrow1 = QPointF(end_x - arrow_size * math.cos(angle - math.pi / 6),
                           end_y - arrow_size * math.sin(angle - math.pi / 6))
        p_arrow2 = QPointF(end_x - arrow_size * math.cos(angle + math.pi / 6),
                           end_y - arrow_size * math.sin(angle + math.pi / 6))

        poly = QPolygonF([QPointF(end_x, end_y), p_arrow1, p_arrow2])
        painter.setBrush(QColor(170, 175, 180))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly)