from __future__ import annotations
from PySide6 import (
    QtWidgets,
    QtCore,
    QtGui,
    QtWebEngineWidgets,
    QtWebEngineCore,
    QtWebChannel,
)
from .util import remove_last_sentence
from .parser import parse as html
from .data_models import Message, Settings
import logging

logger = logging.getLogger(__name__)


class MessageView(Message):
    _page: QtWebEngineCore.QWebEnginePage
    _handle: str

    def __init__(
        self,
        page: QtWebEngineCore.QWebEnginePage,
        index: int,
        role: str,
        content: str,
    ):
        super().__init__(role=role, content=content)
        self._page = page
        self._handle = f"p_{index}"
        if not content:
            if role == "assistant":
                code = "Thinking..."
            else:
                code = ""
        else:
            code = html(content)
        if code:
            self._js(
                f"{self._handle} = document.createElement('p');"
                f"{self._handle}.classList.add('{self.role}');"
                f"{self._handle}.onclick = function() {{ web_bridge.edit_message('{self._handle}'); }};"
                f"{self._handle}.innerHTML = '{code}';"
                f"document.body.appendChild({self._handle});"
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            if not content and role == "assistant":
                self._js(f"{self._handle}.classList.add('thinking');")
        else:
            self._js("window.scrollTo(0, document.body.scrollHeight);")

    def _js(self, code: str):
        self._page.runJavaScript(code)

    def set_content(self, content: str):
        self.content = content
        self._update_view()

    @QtCore.Slot(str)
    def add_chunk(self, chunk: str):
        self.content += chunk
        self._update_view()

    def remove_last_sentence(self):
        self.set_content(remove_last_sentence(self.content))

    def _update_view(self, override: str = ""):
        code = override if override else html(self.content)
        self._js(
            f"{self._handle}.classList.remove('thinking');"
            f"{self._handle}.innerHTML = '{code}';"
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def __del__(self):
        if self._handle:  # to suppress this code if necessary
            try:
                self._js(f"document.body.removeChild({self._handle});")
            except RuntimeError:
                pass

    def mark(self):
        self._js(f"{self._handle}.classList.add('mark');")

    def unmark(self):
        self._js(f"{self._handle}.classList.remove('mark');")


class EditDialog(QtWidgets.QDialog):
    def __init__(self, text: str, parent):
        super().__init__(parent)
        self.setWindowTitle("Edit message")

        self.text_edit = QtWidgets.QTextEdit(self)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlainText(text)
        self.text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.text_edit)
        layout.addWidget(button_box)

    def result(self):
        return self.text_edit.toPlainText()


class WebBridge(QtCore.QObject):
    def __init__(self, parent):
        super().__init__(parent)

    @QtCore.Slot(str)
    def edit_message(self, paragraph_id: str):
        chat_area: ChatArea = self.parent()
        idx = int(paragraph_id[2:])
        logger.info(f"Edit message {idx}")
        message = chat_area._messages[idx]
        dialog = EditDialog(message.content, chat_area)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            message.set_content(dialog.result())


class ChatArea(QtWebEngineWidgets.QWebEngineView):
    _settings: Settings
    _messages: list[MessageView]

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(QtGui.Qt.ContextMenuPolicy.NoContextMenu)
        self._settings = settings
        self._messages = []

        # Web channel setup
        channel = QtWebChannel.QWebChannel(self)
        channel.registerObject("web_bridge", WebBridge(self))
        self.page().setWebChannel(channel)

        # must be last
        self.clear()

    def add(self, role: str, content: str):
        m = MessageView(self.page(), len(self._messages), role, content)
        self._messages.append(m)
        return m

    def get_messages(self) -> list[MessageView]:
        return self._messages

    def clear(self):
        # prevent MessageView.__del__
        for m in self._messages:
            m._handle = ""
        self._messages = []
        self.setHtml(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script>
        var web_bridge;
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            web_bridge = channel.objects.web_bridge;
        }});
    </script>
</head>
<style>
p {{
    min-height: 1em;
    padding: 5px;
    border-radius: 5px;
    width: auto;
    background-color: #AEAEAE;
    margin: 3px;
    font-family: {self._settings.font};
    font-size: {self._settings.font_size}pt;
}}
.user {{
    background-color: {self._settings.user_color};
    margin-left: 50px;
}}
.assistant {{
    background-color: {self._settings.assistant_color};
    margin-right: 50px;
}}
.thinking {{
  animation: pulse 0.5s infinite alternate; /* Apply animation */
}}
@keyframes pulse {{
  0% {{
    background-color: {self._settings.assistant_color}; /* Color at the start */
  }}
  100% {{
    background-color: {self._settings.user_color}; /* Color at the end */
  }}
}}
.mark {{
    border: 1px solid black;
}}
em {{
    font-style: italic;
    color: {self._settings.em_color};
}}
</style>
<body>
</body>
</html>
""")
        self.wait_for_load()

    def wait_for_load(self):
        loop = QtCore.QEventLoop()
        self.loadFinished.connect(loop.quit)
        loop.exec()


class TextEdit(QtWidgets.QTextEdit):
    sendMessage = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
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

    def text(self):
        return self.toPlainText().strip()

    def set_text(self, text: str):
        self.setPlainText(text)


class InputArea(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(0, 100)

        self.edit = TextEdit(self)
        self.summary_button = QtWidgets.QPushButton("Summary", self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.summary_button)
        layout.setSpacing(1)
        layout.setContentsMargins(3, 0, 3, 0)

    def setEnabled(self, yes):
        super().setEnabled(yes)
        if yes:
            self.edit.setFocus()

    def clear(self):
        self.edit.clear()

    def text(self):
        return self.edit.text()

    def set_text(self, text: str):
        return self.edit.set_text(text)

    def add_user_text(self, chunk: str):
        cursor = self.edit.textCursor()
        cursor.insertText(chunk)
        self.edit.setTextCursor(cursor)


class ChatWidget(QtWidgets.QSplitter):
    sendMessage = QtCore.Signal()
    sendSummaryClick = QtCore.Signal()

    def __init__(self, settings: Settings, parent):
        super().__init__(QtCore.Qt.Orientation.Vertical, parent)
        self.setFont(QtGui.QFont(settings.font, settings.font_size))
        self._chat_area = ChatArea(settings, self)
        self._input_area = InputArea(self)
        self.addWidget(self._chat_area)
        self.addWidget(self._input_area)
        self.setSizes([300, 100])

        self._input_area.edit.sendMessage.connect(self.new_user_message)
        self._input_area.summary_button.clicked.connect(self.sendSummaryClick)

    def clear(self):
        self._chat_area.clear()
        # self._input_area.clear()

    @QtCore.Slot(str)
    def new_user_message(self, text: str):
        self._chat_area.add("user", text)
        self.sendMessage.emit()

    def get_user_text(self):
        return self._input_area.text()

    def set_input_text(self, text):
        self._input_area.set_text(text)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Return:
            self._input_area.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def add(self, role: str, content: str) -> MessageView:
        return self._chat_area.add(role, content)

    def get_messages(self) -> list[MessageView]:
        return self._chat_area.get_messages()

    def load_messages(self, messages: list[Message]):
        self.setUpdatesEnabled(False)
        self.clear()
        if messages and messages[-1].role == "user":
            m = messages.pop()
            self.set_input_text(m.content)
        for m in messages:
            self.add(m.role, m.content)
        self.setUpdatesEnabled(True)

    def rewind(self, partial: bool):
        messages = self.get_messages()
        if len(messages) < 2:
            return

        assistant_message = messages[-1]
        assert assistant_message.role == "assistant"
        if partial:
            assistant_message.remove_last_sentence()
            if assistant_message.content:
                return
        # delete assistant message
        messages.pop()
        user_message = messages.pop()
        assert user_message.role == "user"
        self.set_input_text(user_message.content)

    @QtCore.Slot(str)
    def add_user_text(self, chunk: str):
        self._input_area.add_user_text(chunk)

    def enable(self):
        self._input_area.setEnabled(True)

    def disable(self):
        self._input_area.setEnabled(False)
