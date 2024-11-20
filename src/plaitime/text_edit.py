from PySide6 import QtWidgets, QtCore, QtGui


class BasicTextEdit(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)

    def text(self):
        return self.toPlainText().strip()

    def set_text(self, text: str):
        self.setPlainText(text.strip())


class TextEdit(BasicTextEdit):
    sendMessage = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(
            "Type here and press Enter to send message. Use Shift+Enter to make a newline."
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        mod = event.modifiers()
        if event.key() == QtCore.Qt.Key.Key_Return:
            if not (mod & QtCore.Qt.KeyboardModifier.ShiftModifier):
                self.sendMessage.emit(self.text())
                self.clear()
                return
        super().keyPressEvent(event)