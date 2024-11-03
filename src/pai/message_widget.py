from PySide6 import QtWidgets, QtCore
from mistune import html
from pai.data_models import Fact


class MessageWidget(QtWidgets.QLabel):
    role: str
    content: str
    facts: list[Fact]

    def __init__(self, role: str, text: str, facts: list[Fact], *, parent=None):
        super().__init__(parent)

        self.setWordWrap(True)
        self.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

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

        self.role = role
        self.set_text(text)  # this sets content
        self.facts = facts

    def set_text(self, text):
        self.content = text
        if not text:
            if self.role == "assistant":
                self.setText("<em>Thinking...</em>")
            else:
                self.hide()
        else:
            self.setText(html(text))

    def set_facts(self, facts: list[Fact]):
        self.facts = facts

    def add_text(self, text):
        self.content += text
        self.setText(html(self.content))

    def dict(self):
        return {"role": self.role, "content": self.content, "facts": self.facts}
