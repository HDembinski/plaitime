from PySide6 import QtWidgets, QtCore
from mistune import html
from .util import remove_last_sentence


class MessageWidget(QtWidgets.QLabel):
    role: str
    content: str

    def __init__(self, role: str, content: str, *, parent=None):
        super().__init__(parent)

        self.setWordWrap(True)
        self.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.role = role
        self.set_content(content)  # this sets content
        self.unmark()

    def set_content(self, content):
        self.content = content
        if not content:
            if self.role == "assistant":
                self.setText("<em>Thinking...</em>")
            else:
                self.hide()
        else:
            self.setText(html(content))

    def add_chunk(self, chunk):
        self.content += chunk
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

    def remove_last_sentence(self):
        self.set_content(remove_last_sentence(self.content))
