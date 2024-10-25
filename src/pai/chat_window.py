import json
from pathlib import Path

import ollama as llm
from PySide6 import QtCore, QtGui, QtWidgets

# import pai.dummy_llm as llm
from pai import CONFIG_DEFAULT, CONFIG_FILE_NAME
from pai.config_dialog import ConfigDialog
from pai.message_widget import MessageWidget


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal AI")
        self.setMinimumSize(600, 500)

        # Initialize configuration and history
        self.config = self.load_config()
        self.conversation_history = []
        if self.config.get("system_prompt"):
            self.conversation_history.append(
                {"role": "system", "content": self.config["system_prompt"]}
            )

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
        self.input_box = QtWidgets.QTextEdit()
        self.input_box.setMaximumHeight(100)
        self.input_box.setPlaceholderText("Type your message here...")
        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        # Configure LLM action
        config_action = QtGui.QAction("Configure AI", self)
        config_action.triggered.connect(self.show_config_dialog)
        settings_menu.addAction(config_action)

        # Save/Load conversation actions
        save_action = QtGui.QAction("Save", self)
        save_action.triggered.connect(self.save_conversation)
        settings_menu.addAction(save_action)

        load_action = QtGui.QAction("Load", self)
        load_action.triggered.connect(self.load_conversation)
        settings_menu.addAction(load_action)

    def load_config(self):
        if not Path(CONFIG_FILE_NAME).exists():
            with open(CONFIG_FILE_NAME, "w") as f:
                json.dump(CONFIG_DEFAULT, f)

        with open(CONFIG_FILE_NAME, "r") as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            json.dump(self.config, f, indent=4)

    def show_config_dialog(self):
        dialog = ConfigDialog(self.config, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self.save_config()

    def save_conversation(self):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Conversation", "", "JSON Files (*.json)"
        )
        if file_name:
            conversation_data = {
                "messages": self.conversation_history,
                "config": self.config,
            }
            with open(file_name, "w") as f:
                json.dump(conversation_data, f, indent=4)

    def load_conversation(self):
        NotImplemented

    def add_message(self, text, is_user=True):
        message = MessageWidget(text, is_user)
        insert_pos = self.messages_layout.count()
        self.messages_layout.insertWidget(insert_pos, message)
        return message

    def scroll_to_bottom(self, _, vmax):
        self.vscrollbar.setValue(vmax)

    def send_message(self):
        # Disable input while processing

        message_text = self.input_box.toPlainText().strip()

        if message_text:
            self.input_box.clear()
            self.input_box.setEnabled(False)
            self.send_button.setEnabled(False)

            # Add user message
            self.add_message(message_text, True)

            # Create response widget with empty text
            response_widget = self.add_message("", False)

            self.generate_response(message_text, response_widget)

            # Re-enable input in the main thread
            self.input_box.setEnabled(True)
            self.send_button.setEnabled(True)

    def is_context_nearly_full(self, converstation_history):
        # estimate number of token
        num_char = 0
        for message in converstation_history:
            num_char += len(message["content"])
        num_token = num_char / 4
        return num_token > self.config.get(
            "context_limit", CONFIG_DEFAULT["context_limit"]
        )

    def generate_response(self, user_input, response_widget):
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})

        # enable endless chatting by clipping the conversation if it gets too long,
        # while keeping the system prompt
        while len(self.conversation_history) > 2 and self.is_context_nearly_full(
            self.conversation_history
        ):
            self.conversation_history = (
                self.conversation_history[:1] + self.conversation_history[3:]
            )

        try:
            # Generate streaming response using Ollama
            response_text = ""
            for response in llm.chat(
                model=self.config["model"],
                messages=self.conversation_history,
                stream=True,
                options={"temperature": self.config["temperature"]},
            ):
                QtCore.QCoreApplication.processEvents()
                chunk = response["message"]["content"]
                response_text += chunk

                # Update UI in the main thread
                response_widget.append_text(chunk)

            # Add assistant's response to conversation history
            self.conversation_history.append(
                {"role": "assistant", "content": response_text}
            )

        except Exception as e:
            error_message = f"Error generating response: {str(e)}\n\n"
            error_message += "Please make sure:\n"
            error_message += "1. Ollama is installed and running\n"
            error_message += f"2. The model '{self.config['model']}' is available\n"
            error_message += "3. You can run 'ollama run modelname' in terminal"
            response_widget.append_text(error_message)
