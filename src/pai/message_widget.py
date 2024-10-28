from PySide6 import QtWidgets, QtCore
from mistune import html


class MessageWidget(QtWidgets.QFrame):
    _role: str
    _content: str

    def __init__(self, text: str, role: str, parent=None):
        super().__init__(parent)

        self.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Raised)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.message = QtWidgets.QLabel()
        self.message.setWordWrap(True)
        self.message.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.message.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._role = role
        self.set_text(text)  # this sets content

        if role == "user":
            self.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border-radius: 10px;
                    margin: 5px 5px 5px 50px;
                    text-align: right;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border-radius: 10px;
                    margin: 5px 50px 5px 5px;
                }
            """)

        layout.addWidget(self.message)

    def set_text(self, text):
        self._content = text
        self.message.setText(html(text))

    def set_thinking(self):
        self.message.setText("...")

    def asdict(self):
        return {"role": self.role, "content": self.content}

    role = QtCore.Property(str, lambda self: self._role)
    content = QtCore.Property(str, lambda self: self._content)
