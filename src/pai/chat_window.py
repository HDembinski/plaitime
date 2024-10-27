import json
import re

import ollama as llm
from PySide6 import QtCore, QtWidgets

# import pai.dummy_llm as llm
from pai import CONFIG_FILE_NAME, CHARACTER_DIRECTORY
from pai.config_dialog import ConfigDialog
from pai.character_bar import CharacterBar
from pai.message_widget import MessageWidget
from pai.data_classes import Character, Config
import dataclasses
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TextEdit(QtWidgets.QTextEdit):
    def __init__(self, callback):
        self.callback = callback
        super().__init__()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self.callback()
            return
        super().keyPressEvent(event)


class ChatWindow(QtWidgets.QMainWindow):
    character: Character
    system_prompt: str

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
        self.input_box = TextEdit(self.send_message)
        self.input_box.setMaximumHeight(100)
        self.input_box.setPlaceholderText("Type your message here...")

        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        # Must be at the end
        config = self.load_config()
        self.system_prompt = config.general_prompt
        self.load_character(config.current_character)

    def reload_messages(self):
        self.messages_widget = QtWidgets.QWidget()
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()
        self.scroll_area.setWidget(self.messages_widget)

        conversation = self.character.conversation
        for message in conversation:
            self.add_message(message["content"], message["role"] == "user")

        num_token = estimate_num_tokens(conversation)
        self.character_bar.update_num_token(num_token)

    def load_config(self):
        return load(CONFIG_FILE_NAME, Config)

    def save_config(self):
        config = Config(
            current_character=self.character_bar.current_character(),
            general_prompt=self.system_prompt,
        )
        save(config, CONFIG_FILE_NAME)

    def load_character(self, name):
        self.character = load(CHARACTER_DIRECTORY / f"{name}.json", Character)
        self.character_bar.set_character_manually(self.character.name)
        self.reload_messages()
        self.context_limit = get_context_size(self.character.model) - 256
        logger.info(f"context limit = {self.context_limit} for {self.character.model}")

    def save_character(self):
        c = self.character
        logger.info(f"saving character {c.name}")
        save(c, CHARACTER_DIRECTORY / f"{c.name}.json")

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        dialog = ConfigDialog(self.character, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            character = dialog.result()
            self.character = character
            self.character_bar.set_character_manually(character.name)
            self.reload_messages()

    def new_character(self):
        self.save_character()
        self.character = Character()
        self.character_bar.set_character_manually("Assistant")
        self.show_config_dialog()

    def switch_character(self, name):
        logger.info(f"switching character to {name}")
        self.save_character()
        self.load_character(name)

    def add_message(self, text, is_user=True):
        message = MessageWidget(text, is_user)
        self.messages_layout.addWidget(message)
        if not is_user and not text:
            message.set_thinking()
        return message

    def scroll_to_bottom(self, _, vmax):
        self.vscrollbar.setValue(vmax)

    def send_message(self):
        user_text = self.input_box.toPlainText().strip()

        if user_text:
            self.input_box.clear()
            self.send_button.setEnabled(False)

            # Add user message
            self.add_message(user_text, True)

            # Add AI response
            self.generate_response(user_text)

            # Re-enable input in the main thread
            self.send_button.setEnabled(True)
            # self.input_box.setFocus()

    def generate_response(self, user_input):
        response_widget = self.add_message("", False)
        QtCore.QCoreApplication.processEvents()

        # always use current system prompt
        system_prompt = self.character.prompt
        if self.character.append_global_prompt:
            system_prompt += "\n" + self.system_prompt

        conversation = self.character.conversation

        num_token = estimate_num_tokens(conversation)

        # enable endless chatting by clipping the conversation if it gets too long
        while len(conversation) > 2 and num_token > self.context_limit:
            logging.info(
                "context nearly full, dropping oldest messages "
                + f"(lenght of conversation = {len(conversation)})"
            )
            # drop oldest user message and response
            conversation = conversation[2:]

        # add user message to conversation history
        conversation.append({"role": "user", "content": user_input})

        try:
            # Generate streaming response using Ollama
            chunks = []
            for response in llm.chat(
                model=self.character.model,
                messages=[{"role": "system", "content": system_prompt}] + conversation,
                stream=True,
                options={"temperature": self.character.temperature},
            ):
                QtCore.QCoreApplication.processEvents()
                chunk = response["message"]["content"]
                chunks.append(chunk)
                response_widget.set_text("".join(chunks))

            # Add assistant's response to conversation history
            conversation.append({"role": "assistant", "content": "".join(chunks)})

        except Exception as e:
            error_message = f"Error generating response: {str(e)}\n\n"
            error_message += "Please make sure:\n"
            error_message += "1. Ollama is installed and running\n"
            error_message += f"2. The model '{self.character['model']}' is available\n"
            error_message += "3. You can run 'ollama run modelname' in terminal"
            response_widget.set_text(error_message)

        num_token = estimate_num_tokens(conversation)
        self.character_bar.update_num_token(num_token)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self.send_button.click()
            return
        super().keyPressEvent(event)


def estimate_num_tokens(conversation):
    # estimate number of token
    num_char = 0
    for message in conversation:
        num_char += len(message["content"])
    return num_char / 4


def get_context_size(model):
    d = llm.show(model)
    m = re.search(r"num_ctx *(\d+)", d["parameters"])
    if m:
        return int(m.group(1))
    else:
        logger.warning(f"num_ctx not found {model}")
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
