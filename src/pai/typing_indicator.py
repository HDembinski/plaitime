from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer


class TypingIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.dots = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.message = QLabel("Thinking")
        layout.addWidget(self.message)

        self.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 10px;
                margin: 5px 5px 5px 50px;
                padding: 10px;
            }
        """)

    def start(self):
        self.timer.start(500)
        self.show()

    def stop(self):
        self.timer.stop()
        self.hide()

    def update_dots(self):
        self.dots = (self.dots % 3) + 1
        self.message.setText("Thinking" + "." * self.dots)
