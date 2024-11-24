from __future__ import annotations
from PySide6 import (
    QtWidgets,
    QtCore,
    QtGui,
    QtWebEngineWidgets,
    QtWebChannel,
)
from .util import remove_last_sentence
from .parser import parse as html
from .data_models import Message, Colors
from .text_edit import InputTextEdit
import logging

logger = logging.getLogger(__name__)


class MessageView(Message):
    _parent: ChatArea
    _handle: str

    def __init__(
        self,
        parent: ChatArea,
        index: int,
        role: str,
        content: str,
    ):
        super().__init__(role=role, content=content)
        self._parent = parent
        self._handle = f"p_{index}"
        if not content:
            if role == "assistant":
                code = "Thinking..."
            else:
                code = ""
        else:
            code = html(content)
        if code:
            self._parent.js(
                f"{self._handle} = document.createElement('p');"
                f"{self._handle}.classList.add('{self.role}');"
                f"{self._handle}.onclick = function() {{ web_bridge.edit_message('{self._handle}'); }};"
                f"{self._handle}.innerHTML = '{code}';"
                f"document.body.appendChild({self._handle});"
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            if not content and role == "assistant":
                self._parent.js(f"{self._handle}.classList.add('thinking');")
        else:
            self._parent.js(
                f"{self._handle} = document.createElement('p');"
                "window.scrollTo(0, document.body.scrollHeight);"
            )

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
        self._parent.js(
            f"{self._handle}.classList.remove('thinking');"
            f"{self._handle}.innerHTML = '{code}';"
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def mark(self):
        self._parent.js(
            "elements = document.getElementsByClassName('mark');"
            "for (let i = 0; i < elements.length; i++) elements[i].classList.remove('mark');"
            f"{self._handle}.classList.add('mark');"
        )

    def __del__(self):
        if self._handle:  # to suppress this code if necessary
            try:
                self._parent.js(f"document.body.removeChild({self._handle});")
            except RuntimeError:
                pass


class EditDialog(QtWidgets.QDialog):
    result: str = ""

    def __init__(self, text: str, parent):
        super().__init__(parent)
        self.setWindowTitle("Edit message")

        self.text_edit = InputTextEdit(self)
        self.text_edit.set_text(text)
        self.text_edit.sendMessage.connect(self.handle_message)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(lambda: self.handle_message(self.text_edit.text()))
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.text_edit)
        layout.addWidget(button_box)

    @QtCore.Slot(str)
    def handle_message(self, text: str):
        self.result = text
        self.accept()


class WebBridge(QtCore.QObject):
    def __init__(self, parent):
        super().__init__(parent)

    @QtCore.Slot(str)
    def edit_message(self, paragraph_id: str):
        chat_area: ChatArea = self.parent()
        idx = int(paragraph_id[2:])
        logger.info(f"Edit message {idx}")
        message = chat_area.messages[idx]
        dialog = EditDialog(message.content, chat_area)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            message.set_content(dialog.result)


class ChatArea(QtWebEngineWidgets.QWebEngineView):
    colors: Colors
    messages: list[MessageView]

    def __init__(self, colors: Colors, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(QtGui.Qt.ContextMenuPolicy.NoContextMenu)
        self.colors = colors
        self.messages = []

        # Web channel setup
        channel = QtWebChannel.QWebChannel(self)
        channel.registerObject("web_bridge", WebBridge(self))
        self.page().setWebChannel(channel)

        # must be last
        self.clear()

    def js(self, code: str):
        self.page().runJavaScript(code)

    def add(self, role: str, content: str):
        m = MessageView(self, len(self.messages), role, content)
        self.messages.append(m)
        return m

    def clear(self):
        # prevent MessageView.__del__
        for m in self.messages:
            m._handle = ""
        self.messages = []
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
    <style>
        p {{
            min-height: 1em;
            padding: 5px;
            border-radius: 5px;
            width: auto;
            background-color: #AEAEAE;
            margin: 3px;
            font-family: {self.font().family()};
            font-size: {self.font().pointSize()}pt;
        }}
        .user {{
            background-color: {self.colors.user};
            margin-left: 50px;
        }}
        .assistant {{
            background-color: {self.colors.assistant};
            margin-right: 50px;
        }}
        .thinking {{
        animation: pulse 0.5s infinite alternate; /* Apply animation */
        }}
        @keyframes pulse {{
        0% {{
            background-color: {self.colors.assistant}; /* Color at the start */
        }}
        100% {{
            background-color: {self.colors.user}; /* Color at the end */
        }}
        }}
        .mark {{
            border: 1px solid black;
        }}
        em {{
            font-style: italic;
            color: {self.colors.em};
        }}
    </style>
</head>
<body>
</body>
</html>
""")
        self.wait_for_load()

    def wait_for_load(self):
        loop = QtCore.QEventLoop()
        self.loadFinished.connect(loop.quit)
        loop.exec()

    def reload_style(self, colors: Colors):
        self.colors = colors
        messages = [Message(role=m.role, content=m.content) for m in self.messages]
        self.clear()
        for m in messages:
            self.add(m.role, m.content)


class ChatWidget(QtWidgets.QSplitter):
    sendMessage = QtCore.Signal()

    def __init__(
        self,
        colors: Colors,
        parent,
    ):
        super().__init__(QtCore.Qt.Orientation.Vertical, parent)
        self._chat_area = ChatArea(colors, self)
        self._input_area = InputTextEdit(self)
        self.addWidget(self._chat_area)
        self.addWidget(self._input_area)
        self.setSizes([300, 100])

        self._input_area.sendMessage.connect(self.new_user_message)

    def reload_style(self, font: QtGui.QFont, colors: Colors):
        self.setFont(font)
        self._chat_area.reload_style(colors)

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

    @property
    def messages(self) -> list[MessageView]:
        return self._chat_area.messages

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
        messages = self.messages
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

    def enable(self):
        self._input_area.setEnabled(True)

    def disable(self):
        self._input_area.setEnabled(False)
