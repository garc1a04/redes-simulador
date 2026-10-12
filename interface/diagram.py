import sys
from PyQt5.QtWidgets import (QWidget,QSizePolicy)
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygon, QFont
from PyQt5.QtCore import Qt, QPoint

class SequenceDiagramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.setMinimumWidth(300)
        self.setMinimumHeight(400) 
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        

    def add_message(self, src, dst, label, status="success"):
        self.messages.append({
            "src": src, 
            "dst": dst, 
            "label": label, 
            "status": status
        })
        
        required_height = 100 + len(self.messages) * 50
        if required_height > self.minimumHeight():
            self.setMinimumHeight(required_height)
            
        self.update()

    def clear(self):
        self.messages = []
        self.setMinimumHeight(400)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height() 

        # Coordenadas X das linhas de tempo
        x_a = w * 0.2
        x_b = w * 0.8

        # 1. Desenhar as linhas de tempo (Lifelines)
        pen_dash = QPen(Qt.black, 2, Qt.DashLine)
        painter.setPen(pen_dash)
        painter.drawLine(int(x_a), 50, int(x_a), int(h))
        painter.drawLine(int(x_b), 50, int(x_b), int(h))

        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.setPen(Qt.black)
        painter.drawText(int(x_a) - 20, 30, "Host A")
        painter.drawText(int(x_b) - 20, 30, "Host B")

        # 2. Desenhar as mensagens (Setas)
        y = 70
        spacing = 50
        painter.setFont(QFont("Arial", 9))

        for msg in self.messages:
            start_x = x_a if msg["src"] == "A" else x_b
            end_x = x_b if msg["src"] == "A" else x_a
            
            is_lost = msg["status"] == "lost"
            is_retransmitted = msg["status"] == "retransmitted"
            
            actual_end_x = (start_x + end_x) / 2 if is_lost else end_x
            end_y = y + 20

            # Lógica de seleção de cores baseada no status
            if is_lost:
                color = QColor(220, 50, 50)  # Vermelho para falha/perda
            elif is_retransmitted:
                color = QColor(255, 140, 0)  # Laranja para retransmissões
            else:
                color = QColor(50, 100, 220) # Azul para sucesso normal
                
            pen = QPen(color, 2, Qt.SolidLine)
            painter.setPen(pen)

            # Linha principal da mensagem
            painter.drawLine(int(start_x), int(y), int(actual_end_x), int(end_y))

            # Texto
            text_x = min(start_x, actual_end_x) + abs(actual_end_x - start_x) / 2 - 30
            text_y = y + 5
            painter.drawText(int(text_x), int(text_y), msg["label"])

            if is_lost:
                painter.setPen(QPen(QColor(255, 0, 0), 3, Qt.SolidLine))
                painter.drawLine(int(actual_end_x) - 5, int(end_y) - 5, int(actual_end_x) + 5, int(end_y) + 5)
                painter.drawLine(int(actual_end_x) - 5, int(end_y) + 5, int(actual_end_x) + 5, int(end_y) - 5)
            else:
                arrow_size = 8
                direction = 1 if end_x > start_x else -1
                
                p1 = QPoint(int(end_x), int(end_y))
                p2 = QPoint(int(end_x) - direction * arrow_size, int(end_y) - arrow_size)
                p3 = QPoint(int(end_x) - direction * arrow_size, int(end_y) + arrow_size)
                
                poly = QPolygon()
                poly.append(p1)
                poly.append(p2)
                poly.append(p3)
                
                painter.setBrush(color)
                painter.drawPolygon(poly)

            y += spacing