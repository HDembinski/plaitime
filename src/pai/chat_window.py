from pydantic import BaseModel
import logging
from pathlib import Path
from typing import TypeVar

import ollama as llm
from PySide6 import QtCore, QtGui, QtWidgets

from pai import CHARACTER_DIRECTORY, CONFIG_FILE_NAME, MEMORY_DIRECTORY
from pai.character_bar import CharacterBar
from pai.config_dialog import ConfigDialog
from pai.data_models import Character, Config, Memory, Message
from pai.generator import Generator
from pai.message_widget import MessageWidget
from pai.util import estimate_num_tokens

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


class ChatWindow(QtWidgets.QMainWindow):
    character: Character = Character()
    generator: Generator | None = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PAI")
        self.setMinimumSize(600, 500)

        # Create top bar
        self.character_bar = CharacterBar()
        self.setMenuWidget(self.character_bar)
        self.character_bar.config_button.clicked.connect(self.show_config_dialog)
        self.character_bar.new_button.clicked.connect(self.new_character)
        self.character_bar.character_selector.currentTextChanged.connect(
            self.switch_character
        )
        self.character_bar.clipboard_button.clicked.connect(self.copy_to_clipboard)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Create scroll area for messages
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.vscrollbar = self.scroll_area.verticalScrollBar()
        self.vscrollbar.rangeChanged.connect(self.scroll_to_bottom)
        layout.addWidget(self.scroll_area)

        # Create input area
        self.input_box = InputBox()
        self.input_box.setMaximumHeight(100)
        self.input_box.setPlaceholderText("Type your message here...")
        self.input_box.sendMessage.connect(self.send_message_and_generate_response)

        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message_and_generate_response)
        layout.addWidget(self.send_button)

        # Must be at the end
        config = self.load_config()
        self.load_character(config.current_character)

    def load_messages(self, prompt: str, conversation: list[Message]):
        self.messages_widget = QtWidgets.QWidget()
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()
        self.scroll_area.setWidget(self.messages_widget)

        n = len(conversation)
        for i, message in enumerate(conversation):
            if i < n - 1 or message.role == "assistant":
                self.add_message(message.role, message.content)
            else:
                self.input_box.setText(message.content)

        num_token = estimate_num_tokens(prompt, conversation)
        self.character_bar.update_num_token(num_token, self.context_size)

    def load_config(self) -> Config:
        return load(CONFIG_FILE_NAME, Config)

    def save_config(self):
        config = Config(current_character=self.character_bar.current_character())
        save(config, CONFIG_FILE_NAME)

    def load_character(self, id: str):
        if not id:
            # load first character
            for fname in sorted(CHARACTER_DIRECTORY.glob("*.json")):
                id = fname.stem
                break
        self.character = load(CHARACTER_DIRECTORY / f"{id}.json", Character)
        names = get_character_names()
        self.character_bar.set_character_manually(names, self.character.name)
        self.context_size = get_context_size(self.character.model)
        memory: Memory = load(MEMORY_DIRECTORY / f"{id}.json", Memory)
        self.load_messages(self.character.prompt, memory.messages)

    def save_character(self):
        c = self.character
        logger.info(f"saving character {c.name}")
        messages = [
            Message(role=message.role, content=message.content)
            for message in self.get_message_widgets()
        ]
        memory = Memory(messages=messages)
        save(c, CHARACTER_DIRECTORY / f"{c.name}.json")
        save(memory, MEMORY_DIRECTORY / f"{c.name}.json")

    def delete_character(self, name: str):
        logger.info(f"deleting character {name}")
        character_file = CHARACTER_DIRECTORY / f"{name}.json"
        conversation_file = MEMORY_DIRECTORY / f"{name}.json"
        for path in [character_file, conversation_file]:
            if path.exists():
                path.unlink()

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        memory = Memory()
        for message in self.get_message_widgets():
            memory.messages.append(Message.model_validate(message.dict()))
        self.configure_character(self.character, memory)

    def configure_character(self, character, memory):
        dialog = ConfigDialog(character, memory, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            r: str | tuple[Character, Memory] = dialog.result()
            if isinstance(r, str):
                self.delete_character(r)
                self.load_character("")
            else:
                character, memory = r
                self.character = character
                names = get_character_names()
                self.character_bar.set_character_manually(names, character.name)
                self.context_size = get_context_size(self.character.model)
                self.load_messages(character.prompt, memory.messages)

    def new_character(self):
        self.save_character()
        self.configure_character(Character(), Memory())
        names = get_character_names()
        self.character_bar.set_character_manually(names, self.character.name)

    def switch_character(self, name):
        logger.info(f"switching character to {name}")
        self.save_character()
        self.load_character(name)

    def add_message(self, role, text):
        message = MessageWidget(role, text)
        self.messages_layout.addWidget(message)
        return message

    def undo_last_response(self):
        messages = self.get_message_widgets()
        if self.generator and self.generator.isRunning():
            assert len(messages) >= 2
            self.generator.interrupt = True
            self.generator.wait()
        else:
            if not messages:
                return
        assistant_message = messages.pop()
        assert assistant_message.role == "assistant"
        user_message = messages.pop()
        assert user_message.role == "user"
        self.input_box.setText(user_message.content)
        for m in (assistant_message, user_message):
            m.setParent(None)
            m.deleteLater()

    def scroll_to_bottom(self, _, vmax):
        self.vscrollbar.setValue(vmax)

    def send_message_and_generate_response(self):
        user_text = self.input_box.toPlainText().strip()
        if not user_text:
            return

        self.input_box.clear()
        self.send_button.setEnabled(False)
        self.input_box.setEnabled(False)
        self.add_message("user", user_text)
        self.generate_response()

    def generator_finished(self):
        self.send_button.setEnabled(True)
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.generator = None

    def generate_response(self):
        self.generator = Generator(
            self.character, self.get_message_widgets(), self.context_size
        )
        mw = self.add_message("assistant", "")
        self.generator.increment.connect(mw.add_text)
        self.generator.error.connect(mw.set_text)
        self.generator.finished.connect(self.generator_finished)
        self.generator.start()

    def copy_to_clipboard(self):
        messages = self.get_message_widgets()
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText("\n\n".join(m.content for m in messages))

    def get_message_widgets(self) -> list[MessageWidget]:
        return [
            child
            for child in self.messages_widget.children()
            if isinstance(child, MessageWidget)
        ]

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            self.undo_last_response()
        else:
            super().keyPressEvent(event)


def get_context_size(model):
    d = llm.show(model)["model_info"]
    for key in d:
        if "context_length" in key:
            return d[key]
    logger.warning(f"context length not found {model}")
    return 4096


def save(obj: BaseModel, filename: Path):
    with open(filename, "w") as f:
        f.write(obj.model_dump_json())


def load(filename: Path, cls: T) -> T:
    if filename.exists():
        with open(filename) as f:
            return cls.model_validate_json(f.read())
    elif cls is Memory and not filename.exists():
        import json

        filename = CHARACTER_DIRECTORY / (filename.stem + ".json")
        with open(filename) as f:
            d = json.load(f)
        return Memory(messages=[Message(**x) for x in d["conversation"]])

    logger.error(f"loading {filename} failed, file does not exist")
    return cls()


def get_character_names():
    names = []
    for fname in CHARACTER_DIRECTORY.glob("*.json"):
        names.append(fname.stem)
    return names
