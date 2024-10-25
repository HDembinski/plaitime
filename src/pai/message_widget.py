from PySide6 import QtWidgets
import mistune


class MessageWidget(QtWidgets.QFrame):
    def __init__(self, text="", is_user=True, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Raised)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.message = QtWidgets.QLabel()
        self.set_text(text)
        self.message.setWordWrap(True)
        self.message.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)

        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border-radius: 10px;
                    margin: 5px 50px 5px 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border-radius: 10px;
                    margin: 5px 5px 5px 50px;
                }
            """)

        layout.addWidget(self.message)

    def append_text(self, text):
        self.set_text(self.markdown + text)

    def set_text(self, text):
        self.markdown = text
        self.message.setText(mistune.html(text))
