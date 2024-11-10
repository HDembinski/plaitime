from PySide6 import QtWidgets, QtCore
from .message_widget import MessageWidget


class InputArea(QtWidgets.QTextEdit):
    sendMessage = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(0, 100)
        self.setAcceptRichText(False)
        self.setPlaceholderText(
            "Type here and press Enter to send message. Use Shift+Enter to make a newline."
        )

    def keyPressEvent(self, event):
        mod = event.modifiers()
        if event.key() == QtCore.Qt.Key_Return:
            if not (mod & QtCore.Qt.KeyboardModifier.ShiftModifier):
                self.sendMessage.emit(self.text())
                self.clear()
                return
        super().keyPressEvent(event)

    def text(self):
        return self.toPlainText().strip()

    def set_text(self, text: str):
        self.setPlainText(text)

    def setEnabled(self, yes):
        super().setEnabled(yes)
        if yes:
            self.setFocus()

    def append_user_text(self, chunk: str):
        cursor = self.textCursor()
        cursor.insertText(chunk)
        self.setTextCursor(cursor)


class ChatWidget(QtWidgets.QSplitter):
    sendMessage = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(QtCore.Qt.Orientation.Vertical, parent)
        self._chat_view = ChatView()
        self._input_area = InputArea()
        self.addWidget(self._chat_view)
        self.addWidget(self._input_area)
        self.setSizes([300, 100])

        self._input_area.sendMessage.connect(self._new_user_message)

    def clear(self):
        self._chat_view.clear()
        self._input_area.clear()

    def _new_user_message(self, text: str):
        self._chat_view.add("user", text)
        self.sendMessage.emit()

    def get_user_text(self):
        return self._input_area.text()

    def set_input_text(self, text):
        self._input_area.set_text(text)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self._input_area.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def add(self, role: str, content: str) -> MessageWidget:
        return self._chat_view.add(role, content)

    def get_messages(self) -> list[MessageWidget]:
        return self._chat_view.get_messages()

    def rewind(self):
        messages = self.get_messages()
        if len(messages) >= 2:
            assistant_message = messages.pop()
            assert assistant_message.role == "assistant"
            user_message = messages.pop()
            assert user_message.role == "user"
            self.set_input_text(user_message.content)
            for m in (assistant_message, user_message):
                m.setParent(None)
                m.deleteLater()

    def append_user_text(self, chunk):
        self._input_area.append_user_text(chunk)

    def enable(self):
        self._input_area.setEnabled(True)

    def disable(self):
        self._input_area.setEnabled(False)


class ChatView(QtWidgets.QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.verticalScrollBar().rangeChanged.connect(
            lambda _, vmax: self.verticalScrollBar().setValue(vmax)
        )
        layout = QtWidgets.QVBoxLayout()
        layout.addStretch(1.0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.scrollable_content = QtWidgets.QWidget()
        self.scrollable_content.setLayout(layout)
        self.setWidget(self.scrollable_content)

    def add(self, role: str, content: str):
        mw = MessageWidget(role, content)
        self.scrollable_content.layout().addWidget(mw)
        return mw

    def get_messages(self) -> list[MessageWidget]:
        return self.scrollable_content.children()[1:]

    def clear(self):
        for child in self.get_messages():
            child.setParent(None)
            child.deleteLater()
