from PySide6 import QtWidgets, QtCore
from mistune import html


class MessageWidget(QtWidgets.QLabel):
    role: str
    content: str

    def __init__(self, role: str, text: str, *, parent=None):
        super().__init__(parent)

        self.setWordWrap(True)
        self.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.role = role
        self.set_text(text)  # this sets content
        self.unmark()

    def set_text(self, text):
        self.content = text
        if not text:
            if self.role == "assistant":
                self.setText("<em>Thinking...</em>")
            else:
                self.hide()
        else:
            self.setText(html(text))

    def add_text(self, text):
        self.content += text
        self.setText(html(self.content))

    def mark(self):
        self.backup_stylesheet = self.styleSheet()
        self.setStyleSheet(
            """
        QFrame {
            background-color: #F5F5F5;
            border-radius: 10px;
            margin: 0px 0px 0px 50px;
            padding: 5px;
            text-align: right;
            border-width: 3px;
            border-style: solid;
            border-color: black;
        }
        """
            if self.role == "user"
            else """
        QFrame {
            background-color: #E3F2FD;
            border-radius: 10px;
            margin: 0px 50px 0px 0px;
            padding: 5px;
            border-width: 3px;
            border-style: solid;
            border-color: black;
        }
        """
        )

    def unmark(self):
        self.setStyleSheet(
            """
        QFrame {
            background-color: #F5F5F5;
            border-radius: 10px;
            margin: 0px 0px 0px 50px;
            padding: 5px;
            text-align: right;
        }
        """
            if self.role == "user"
            else """
        QFrame {
            background-color: #E3F2FD;
            border-radius: 10px;
            margin: 0px 50px 0px 0px;
            padding: 5px;
        }
        """
        )
