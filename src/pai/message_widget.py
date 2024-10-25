from PySide6 import QtGui, QtWidgets


class MessageWidget(QtWidgets.QFrame):
    def __init__(self, text="", is_user=True, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Raised)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.message = QtWidgets.QLabel()
        self.message.setText(text)
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
        pre = self.message.text()
        cur = pre + text
        self.message.setText(cur)
        # cursor = self.message.textCursor()
        # cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        # cursor.insertText(text)
        # self.message.setTextCursor(cursor)
