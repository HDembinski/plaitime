import logging

import ollama
from ollama import ResponseError
from PySide6 import QtCore, QtGui, QtWidgets

from . import (
    CHARACTER_DIRECTORY,
    CONFIG_FILE_NAME,
    MEMORY_DIRECTORY,
    STORY_EXTRACTION_PROMPT,
    CONTEXT_MARGIN_FRACTION,
    CHARACTERS_PER_TOKEN,
)
from .character_bar import CharacterBar
from .config_dialog import ConfigDialog
from .data_models import Character, Config, Memory, Message
from .generator import Generator
from .chat_widget import ChatWidget
from .util import estimate_num_tokens
from .io import load, save
from typing import Callable

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class InputBox(QtWidgets.QTextEdit):
    sendMessage = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)

    def keyPressEvent(self, event):
        mod = event.modifiers()
        match event.key():
            case QtCore.Qt.Key_Return:
                if not (mod & QtCore.Qt.KeyboardModifier.ShiftModifier):
                    self.sendMessage.emit()
                    return
        super().keyPressEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    character: Character
    generator: Generator | None
    cancel_action: Callable

    def __init__(self):
        super().__init__()
        self.character = Character()
        self.generator = None
        self.cancel_action = self.undo_last_response

        self.setWindowTitle("Plaitime")
        self.setMinimumSize(600, 500)

        # Create top bar
        self.character_bar = CharacterBar()
        self.setMenuWidget(self.character_bar)
        self.character_bar.config_button.clicked.connect(self.show_config_dialog)
        self.character_bar.new_button.clicked.connect(self.new_character)
        self.character_bar.summary_button.clicked.connect(self.generate_summary)
        self.character_bar.character_selector.currentTextChanged.connect(
            self.switch_character
        )
        self.character_bar.clipboard_button.clicked.connect(self.copy_to_clipboard)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Create scroll area for messages
        self.chat_widget = ChatWidget(self)
        layout.addWidget(self.chat_widget)

        # Create input area
        self.input_box = InputBox()
        self.input_box.setMaximumHeight(100)
        self.input_box.setPlaceholderText("Type here...")
        self.input_box.sendMessage.connect(self.send_message_and_generate_response)

        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message_and_generate_response)
        layout.addWidget(self.send_button)

        # Must be at the end
        config = self.load_config()
        self.load_character(config.current_character)

    def load_messages(self, prompt: str, memory: Memory):
        self.chat_widget.clear()

        messages = memory.messages
        if messages and messages[-1].role == "user":
            m = messages.pop()
            self.input_box.setText(m.content)
        for m in messages:
            self.chat_widget.add(m.role, m.content)

        num_token = estimate_num_tokens(prompt, messages)
        self.character_bar.update_num_token(num_token, self.context_size)

    def load_config(self) -> Config:
        return load(CONFIG_FILE_NAME, Config)

    def save_config(self):
        config = Config(current_character=self.character_bar.current_character())
        save(config, CONFIG_FILE_NAME)

    def load_character(self, name: str):
        if not name:
            # load any character
            for fname in CHARACTER_DIRECTORY.glob("*.json"):
                name = fname.stem
                break
        self.character = load(CHARACTER_DIRECTORY / f"{name}.json", Character)
        warmup_model(self.character.model, self)
        names = get_character_names()
        self.character_bar.set_character_manually(names, self.character.name)
        self.context_size = get_context_size(self.character.model)
        memory = load(MEMORY_DIRECTORY / f"{name}.json", Memory)
        self.input_box.clear()
        self.load_messages(self.character.prompt, memory)

    def save_character(self):
        c = self.character
        logger.info(f"saving character {c.name}")
        save(c, CHARACTER_DIRECTORY / f"{c.name}.json")

        if c.save_conversation:
            widgets = self.chat_widget.get_messages()
            messages = [Message(role=w.role, content=w.content) for w in widgets]
            user_text = self.get_user_text()
            if user_text:
                messages.append(Message(role="user", content=user_text))
            if messages:
                memory = Memory(messages=messages)
                save(memory, MEMORY_DIRECTORY / f"{c.name}.json")
                return
        # if nothing shall be saved if there is nothing to save, remove the file
        path = MEMORY_DIRECTORY / f"{c.name}.json"
        path.unlink(missing_ok=True)

    def delete_character(self, name: str):
        logger.info(f"deleting character {name}")
        for path in (
            CHARACTER_DIRECTORY / f"{name}.json",
            MEMORY_DIRECTORY / f"{name}.json",
        ):
            path.unlink(missing_ok=True)

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        widgets = self.chat_widget.get_messages()
        messages = []
        for w in widgets:
            messages.append(Message(role=w.role, content=w.content))
        self.configure_character(self.character, Memory(messages=messages))

    def configure_character(self, character: Character, memory: Memory):
        dialog = ConfigDialog(character.model_copy(), memory.model_copy(), parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            r: str | tuple[Character, Memory] = dialog.result()
            if isinstance(r, str):
                self.delete_character(r)
                self.load_character("")
            else:
                character, memory = r
                if self.character.name != character.name:
                    self.delete_character(self.character.name)
                self.character = character
                names = get_character_names()
                self.character_bar.set_character_manually(names, character.name)
                self.context_size = get_context_size(self.character.model)
                self.load_messages(character.prompt, memory)

    def new_character(self):
        self.save_character()
        # this is important, otherwise the old character is deleted in configure_character
        self.character = Character()
        self.memory = Memory()
        self.configure_character(self.character, self.memory)
        names = get_character_names()
        self.character_bar.set_character_manually(names, self.character.name)

    def switch_character(self, name):
        logger.info(f"switching character to {name}")
        self.save_character()
        self.load_character(name)

    def undo_last_response(self):
        self.cancel_generator()

        messages = self.chat_widget.get_messages()
        if len(messages) >= 2:
            assistant_message = messages.pop()
            assert assistant_message.role == "assistant"
            user_message = messages.pop()
            assert user_message.role == "user"
            self.input_box.setText(user_message.content)
            for m in (assistant_message, user_message):
                m.setParent(None)
                m.deleteLater()

    def get_user_text(self):
        return self.input_box.toPlainText().strip()

    def send_message_and_generate_response(self):
        user_text = self.get_user_text()
        self.input_box.clear()
        self.send_button.setEnabled(False)
        self.input_box.setEnabled(False)
        self.chat_widget.add("user", user_text)
        self.generate_response()

    def generator_finished(self):
        self.send_button.setEnabled(True)
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.generator = None
        estimate_num_tokens(self.character.prompt, self.chat_widget.get_messages())

    def generate_response(self):
        prompt = self.character.prompt

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        window = []
        num_token = len(prompt) / CHARACTERS_PER_TOKEN
        for w in reversed(self.chat_widget.get_messages()):
            w.unmark()
            window.append({"role": w.role, "content": w.content})
            num_token += len(w.content) / CHARACTERS_PER_TOKEN
            if num_token > self.context_size * (1 - CONTEXT_MARGIN_FRACTION):
                break
        assert len(window) > 0
        assert w.content == window[-1]["content"]
        w.mark()
        window.append({"role": "system", "content": prompt})
        window.reverse()

        self.generator = Generator(
            self.character.model, window, temperature=self.character.temperature
        )
        mw = self.chat_widget.add("assistant", "")
        self.generator.nextChunk.connect(mw.add_chunk)
        self.generator.error.connect(mw.set_content)
        self.generator.finished.connect(self.generator_finished)
        self.cancel_action = self.undo_last_response
        self.generator.start()

    def get_dialog_as_text(self):
        messages = self.chat_widget.get_messages()
        text = self.character.prompt + "\n\n".join(
            f"{m.role.capitalize()}:\n{m.content}" for m in messages
        )
        return text

    def copy_to_clipboard(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(self.get_dialog_as_text())

    def generate_summary(self):
        self.send_button.setEnabled(False)

        prompt = STORY_EXTRACTION_PROMPT.format(self.get_dialog_as_text())

        logger.info(prompt)

        self.generator = Generator(
            self.character.model,
            messages=(
                # {"role": "system", "content": ""},
                {"role": "user", "content": prompt},
            ),
            temperature=0.1,
        )

        def append_text(chunk):
            cursor = self.input_box.textCursor()
            cursor.insertText(chunk)
            self.input_box.setTextCursor(cursor)

        self.generator.nextChunk.connect(append_text)
        self.generator.finished.connect(self.generate_summary_finished)
        self.cancel_action = self.cancel_generator
        self.generator.start()

    def generate_summary_finished(self):
        self.generator = None
        self.send_button.setEnabled(True)

    def cancel_generator(self):
        if self.generator and self.generator.isRunning():
            self.generator.interrupt = True
            self.generator.wait()
            self.generator = None
        self.cancel_action = self.undo_last_response

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            self.cancel_action()
        else:
            super().keyPressEvent(event)


def get_context_size(model):
    try:
        d = ollama.show(model)["model_info"]
        for key in d:
            if "context_length" in key:
                return d[key]
        raise RuntimeError("context_length not found")
        # model was removed
    except ResponseError:
        return 0


def get_character_names():
    names = []
    for fname in CHARACTER_DIRECTORY.glob("*.json"):
        names.append(fname.stem)
    return names


def warmup_model(model, parent):
    thread = QtCore.QThread(parent)
    thread.run = lambda: ollama.generate(model=model, prompt="", keep_alive="1h")
    thread.finished.connect(thread.deleteLater)
    thread.start()
