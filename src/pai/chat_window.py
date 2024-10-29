import dataclasses
import json
import logging

import ollama as llm
from PySide6 import QtCore, QtWidgets

# import pai.dummy_llm as llm
from pai import CHARACTER_DIRECTORY, CONFIG_FILE_NAME
from pai.character_bar import CharacterBar
from pai.config_dialog import ConfigDialog
from pai.data_classes import Character, Config
from pai.message_widget import MessageWidget
from pai.util import get_messages, estimate_num_tokens
from pai.generator import Generator

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

    def load_messages(self, character):
        self.messages_widget = QtWidgets.QWidget()
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()
        self.scroll_area.setWidget(self.messages_widget)

        n = len(character.conversation)
        for i, message in enumerate(character.conversation):
            if i < n - 1 or message["role"] == "assistant":
                self.add_message(message["content"], message["role"])
            else:
                self.input_box.setText(message["content"])

        num_token = estimate_num_tokens(character.prompt, character.conversation)
        self.character_bar.update_num_token(num_token, self.context_size)

    def load_config(self):
        return load(CONFIG_FILE_NAME, Config)

    def save_config(self):
        config = Config(current_character=self.character_bar.current_character())
        save(config, CONFIG_FILE_NAME)

    def load_character(self, name: str):
        if not name:
            for fname in sorted(CHARACTER_DIRECTORY.glob("*.json")):
                name = fname.stem
                break
            character = (
                load(CHARACTER_DIRECTORY / f"{name}.json", Character)
                if name
                else Character()
            )
        else:
            character = load(CHARACTER_DIRECTORY / f"{name}.json", Character)
        self.character = character
        self.character_bar.set_character_manually(self.character.name)
        self.context_size = get_context_size(self.character.model)
        self.load_messages(self.character)

    def save_character(self):
        c = self.character
        logger.info(f"saving character {c.name}")
        c.conversation = []
        if c.save_conversation:
            for message in get_messages(self.messages_widget):
                c.conversation.append(message.asdict())
        save(c, CHARACTER_DIRECTORY / f"{c.name}.json")

    def delete_character(self, name: str):
        logger.info(f"deleting character {name}")
        (CHARACTER_DIRECTORY / f"{name}.json").unlink()

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        self.save_character()
        self.configure_character(self.character)

    def configure_character(self, character):
        dialog = ConfigDialog(character, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            character = dialog.result()
            if isinstance(character, str):
                self.delete_character(character)
                self.load_character("")
            else:
                self.character = character
                self.character_bar.set_character_manually(character.name)
                self.context_size = get_context_size(self.character.model)
                self.load_messages(character)

    def new_character(self):
        self.save_character()
        self.configure_character(Character())
        self.character_bar.set_character_manually(self.character.name)

    def switch_character(self, name):
        logger.info(f"switching character to {name}")
        self.save_character()
        self.load_character(name)

    def add_message(self, text, role):
        message = MessageWidget(text, role)
        self.messages_layout.addWidget(message)
        return message

    def undo_last_response(self):
        messages = get_messages(self.messages_widget)
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
        self.input_box.setDisabled(True)
        self.add_message(user_text, "user")
        self.generate_response()

    def generator_finished(self):
        self.send_button.setEnabled(True)
        self.input_box.setEnabled(True)
        self.generator = None

    def generate_response(self):
        self.generator = Generator(
            self.character, get_messages(self.messages_widget), self.context_size
        )
        mw = self.add_message("", "assistant")
        self.generator.increment.connect(mw.add_text)
        self.generator.error.connect(mw.set_text)
        self.generator.finished.connect(self.generator_finished)
        self.generator.start()

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


def save(data_obj, filename):
    d = dataclasses.asdict(data_obj)
    with open(filename, "w") as f:
        json.dump(d, f, indent=4)


def load(filename, cls):
    try:
        with open(filename) as f:
            d = json.load(f)
        return cls(**d)
    except Exception as e:
        logger.error(f"loading of {filename} failed:\n{e}")
        return cls()
