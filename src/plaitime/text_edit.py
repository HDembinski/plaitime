from PySide6 import QtWidgets, QtCore, QtGui


class TextEditor(QtWidgets.QWidget):
    generateClicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = BasicTextEdit(self)
        self.button = QtWidgets.QPushButton("Generate", self)
        self.button.clicked.connect(self.generateClicked)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

    def text(self) -> str:
        return self.edit.text()

    def set_text(self, text: str):
        self.edit.set_text(text)

    def add_chunk(self, chunk: str):
        self.edit.add_chunk(chunk)

    def move_cursor_to_end(self):
        self.edit.move_cursor_to_end()

    def setFont(self, font: QtGui.QFont):
        self.edit.setFont(font)


class BasicTextEdit(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)

    def text(self):
        return self.toPlainText().strip()

    def set_text(self, text: str):
        self.setPlainText(text.strip())

    def add_chunk(self, chunk: str):
        cursor = self.textCursor()
        cursor.insertText(chunk)
        self.setTextCursor(cursor)

    def setEnabled(self, yes):
        self.setReadOnly(not yes)
        if yes:
            self.setFocus()

    def move_cursor_to_end(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText("\n")
        self.setTextCursor(cursor)


class InputTextEdit(BasicTextEdit):
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
