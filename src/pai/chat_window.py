import dataclasses
import json
import logging
from contextlib import contextmanager

import ollama as llm
from PySide6 import QtCore, QtWidgets, QtGui

# import pai.dummy_llm as llm
from pai import CHARACTER_DIRECTORY, CONFIG_FILE_NAME
from pai.character_bar import CharacterBar
from pai.config_dialog import ConfigDialog
from pai.data_classes import Character, Config
from pai.message_widget import MessageWidget

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


CHARACTERS_PER_TOKEN = 4  # on average
CONTEXT_MARGIN = 512


@contextmanager
def generating(self):
    self.is_generating = True
    self.stop_generation = False
    try:
        yield
    finally:
        self.is_generating = False
        self.stop_generation = False


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
    is_generating: bool = False
    stop_generation: bool = False

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
        self.input_box.sendMessage.connect(self.send_message)

        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
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
            for message in self.get_messages():
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
        if role == "assistant" and not text:
            message.set_thinking()
        return message

    def get_messages(self):
        return [
            child
            for child in self.messages_widget.children()
            if isinstance(child, MessageWidget)
        ]

    def undo_last_response(self):
        messages = self.get_messages()
        if self.is_generating:
            assert len(messages) >= 2
            self.stop_generation = True
            # see code in generate_message
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

    def send_message(self):
        user_text = self.input_box.toPlainText().strip()

        if user_text:
            self.input_box.clear()
            self.send_button.setEnabled(False)

            self.add_message(user_text, "user")
            self.generate_response(user_text)

            # Re-enable input in the main thread
            self.send_button.setEnabled(True)
            # self.input_box.setFocus()

    def generate_response(self, user_input):
        # we always use current system prompt
        system_prompt = self.character.prompt or "You are a helpful AI assistant."
        messages = self.get_messages()

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        conversation_window = []
        num_token = len(system_prompt)
        i = len(messages) - 1
        while num_token < self.context_size - CONTEXT_MARGIN and i >= 0:
            message = messages[i]
            conversation_window.append(message.asdict())
            i -= 1
            num_token += len(message.content)
        num_token /= CHARACTERS_PER_TOKEN
        conversation_window.append({"role": "system", "content": system_prompt})
        conversation_window.reverse()

        with generating(self):
            response_widget = self.add_message("", "assistant")
            QtCore.QCoreApplication.processEvents()
            try:
                # Generate streaming response using Ollama
                chunks = []
                for response in llm.chat(
                    model=self.character.model,
                    messages=conversation_window,
                    stream=True,
                    options={"temperature": self.character.temperature},
                ):
                    QtCore.QCoreApplication.processEvents()
                    if self.stop_generation:
                        break
                    chunk = response["message"]["content"]
                    chunks.append(chunk)
                    response_widget.set_text("".join(chunks))
            except Exception as e:
                error_message = f"""Error generating response: {str(e)}\n\n
Please make sure that the model '{self.character.model}' is available.
You can run 'ollama run {self.character.model}' in terminal to check."""
                response_widget.set_text(error_message)

        num_token = estimate_num_tokens(system_prompt, [x.asdict() for x in messages])
        self.character_bar.update_num_token(num_token, self.context_size)

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            self.undo_last_response()
        else:
            super().keyPressEvent(event)


def estimate_num_tokens(prompt, conversation):
    # estimate number of token
    num_char = len(prompt)
    for message in conversation:
        num_char += len(message["content"])
    return num_char / CHARACTERS_PER_TOKEN


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
