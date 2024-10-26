import json
from pathlib import Path

import ollama as llm
from PySide6 import QtCore, QtGui, QtWidgets

# import pai.dummy_llm as llm
from pai import CONFIG_DEFAULT, CONFIG_FILE_NAME, CHARACTER_DEFAULT, CHARACTER_DIRECTORY
from pai.config_dialog import ConfigDialog
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

        # Initialize configuration
        self.config = self.load_config()
        self.character = self.load_character(self.config["current_character"])

        # Create menu bar
        self.create_menu_bar()

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Create scroll area for messages
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.vscrollbar = scroll_area.verticalScrollBar()
        self.vscrollbar.rangeChanged.connect(self.scroll_to_bottom)

        # Create widget to hold messages
        self.messages_widget = QtWidgets.QWidget()
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()

        scroll_area.setWidget(self.messages_widget)
        layout.addWidget(scroll_area)

        # Create input area
        self.input_box = TextEdit(self.send_message)
        self.input_box.setMaximumHeight(100)
        self.input_box.setPlaceholderText("Type your message here...")

        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        # replay chat
        for message in self.character["conversation"]:
            self.add_message(message["content"], message["role"] == "user")

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        # Configure LLM action
        config_action = QtGui.QAction("Configure", self)
        config_action.triggered.connect(self.show_config_dialog)
        settings_menu.addAction(config_action)

    def load_config(self):
        if not Path(CONFIG_FILE_NAME).exists():
            with open(CONFIG_FILE_NAME, "w") as f:
                json.dump(CONFIG_DEFAULT, f)

        with open(CONFIG_FILE_NAME, "r") as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            json.dump(self.config, f, indent=4)

    def load_character(self, name):
        if not name:
            return CHARACTER_DEFAULT

        with open(CHARACTER_DIRECTORY / f"{name}.json") as f:
            return json.load(f)

    def save_character(self):
        name = self.config["current_character"]
        with open(CHARACTER_DIRECTORY / f"{name}.json", "w") as f:
            json.dump(self.character, f)

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        dialog = ConfigDialog(self.character, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.character.update(dialog.get_config())
            self.config["current_character"] = self.character["name"]
            self.save_all()

    def add_message(self, text, is_user=True):
        message = MessageWidget(text, is_user)
        insert_pos = self.messages_layout.count()
        self.messages_layout.insertWidget(insert_pos, message)
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

    def is_context_nearly_full(self, converstation):
        # estimate number of token
        num_char = 0
        for message in converstation:
            num_char += len(message["content"])
        num_token = num_char / 4
        logging.info(f"current estimated number of tokens: {num_token}")
        return num_token > self.character.get(
            "context_limit", CHARACTER_DEFAULT["context_limit"]
        )

    def generate_response(self, user_input):
        response_widget = self.add_message("", False)

        # always use current system prompt
        system_prompt = self.character["system_prompt"]
        conversation = self.character["conversation"]

        # enable endless chatting by clipping the conversation if it gets too long
        while len(conversation) > 2 and self.is_context_nearly_full(conversation):
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

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self.send_message()
            return
        super().keyPressEvent(event)
