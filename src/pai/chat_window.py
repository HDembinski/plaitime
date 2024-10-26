import json
import re

import ollama as llm
from PySide6 import QtCore, QtWidgets

# import pai.dummy_llm as llm
from pai import CONFIG_DEFAULT, CONFIG_FILE_NAME, CHARACTER_DEFAULT, CHARACTER_DIRECTORY
from pai.config_dialog import ConfigDialog
from pai.top_bar import TopBar
from pai.message_widget import MessageWidget
import logging

logger = logging.getLogger()


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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PAI")
        self.setMinimumSize(600, 500)

        # Create top bar
        self.top_bar = TopBar()
        self.setMenuWidget(self.top_bar)
        self.top_bar.config_button.clicked.connect(self.show_config_dialog)
        self.top_bar.new_button.clicked.connect(self.new_character)
        self.top_bar.character_selector.currentTextChanged.connect(
            self.switch_to_character
        )
        self.top_bar.clear_button.clicked.connect(self.clear_conversation)

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
        self.general_system_prompt = config["general_prompt"]
        self.load_character(config["current_character"])

    def new_messages_widget(self):
        self.messages_widget = QtWidgets.QWidget()
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()
        self.scroll_area.setWidget(self.messages_widget)

        # replay chat
        conversation = self.character["conversation"]
        for message in conversation:
            self.add_message(message["content"], message["role"] == "user")

        num_token = estimate_num_tokens(conversation)
        self.top_bar.update_num_token(num_token)

    def load_config(self):
        config = CONFIG_DEFAULT.copy()
        try:
            with open(CONFIG_FILE_NAME, "r") as f:
                config.update(json.load(f))
        except IOError:
            pass
        return config

    def save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            config = {
                "current_character": self.top_bar.current_character(),
                "general_prompt": self.general_system_prompt,
            }
            json.dump(config, f, indent=4)

    def load_character(self, name):
        self.character = {**CHARACTER_DEFAULT}
        try:
            with open(CHARACTER_DIRECTORY / f"{name}.json") as f:
                self.character.update(json.load(f))
            self.top_bar.update(name)
        except Exception:
            logger.error(f"loading character {name} failed")
            self.top_bar.update("Assistant")
        self.save_config()
        self.new_messages_widget()
        self.context_limit = get_context_size(self.character["model"]) - 256
        logger.info(
            f"context limit = {self.context_limit} for {self.character['model']}"
        )

    def save_character(self):
        c = self.load_config()
        name = c["current_character"]
        if name == "Assistant":
            return
        logger.info(f"saving character {name}")
        with open(CHARACTER_DIRECTORY / f"{name}.json", "w") as f:
            json.dump(self.character, f, indent=4)
        self.top_bar.update(name)

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        dialog = ConfigDialog(self.top_bar.current_character(), self.character, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            name, c = dialog.result()
            self.character.update(c)
            self.top_bar.update(name)
            self.save_config()
            self.save_character()

    def new_character(self):
        self.character = {**CHARACTER_DEFAULT}
        self.top_bar.update("Assistant")
        self.save_config()
        self.show_config_dialog()

    def switch_to_character(self, name):
        # save_character takes old name from load_config
        self.save_character()
        self.load_character(name)

    def clear_conversation(self):
        self.character["conversation"] = []
        self.new_messages_widget()

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
        system_prompt = (
            self.character["prompt"]
            + "\n"
            + self.general_system_prompt.format(name=self.top_bar.current_character())
        )

        conversation = self.character["conversation"]

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
                model=self.character["model"],
                messages=[{"role": "system", "content": system_prompt}] + conversation,
                stream=True,
                options={"temperature": self.character["temperature"]},
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
        self.top_bar.update_num_token(num_token)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self.send_message()
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
