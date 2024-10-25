import sys
import json
import threading
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QDialog,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QTabWidget,
    QFormLayout,
    QDoubleSpinBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor, QFont, QAction
import ollama
from pathlib import Path

CONFIG_FILE_NAME = f"{Path(__file__).basename}.cfg"


class TypingIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.dots = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.message = QLabel("Thinking")
        layout.addWidget(self.message)

        self.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 10px;
                margin: 5px 5px 5px 50px;
                padding: 10px;
            }
        """)

    def start(self):
        self.timer.start(500)
        self.show()

    def stop(self):
        self.timer.stop()
        self.hide()

    def update_dots(self):
        self.dots = (self.dots % 3) + 1
        self.message.setText("Thinking" + "." * self.dots)


class ConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("LLM Configuration")
        self.setMinimumWidth(500)

        tabs = QTabWidget()

        # System Prompt Tab
        system_prompt_widget = QWidget()
        system_prompt_layout = QVBoxLayout()

        self.system_prompt = QTextEdit()
        self.system_prompt.setPlainText(config["system_prompt"])
        self.system_prompt.setMinimumHeight(200)

        system_prompt_layout.addWidget(QLabel("System Prompt"))
        system_prompt_layout.addWidget(self.system_prompt)
        system_prompt_widget.setLayout(system_prompt_layout)
        tabs.addTab(system_prompt_widget, "System Prompt")

        # Model Parameters Tab
        params_widget = QWidget()
        params_layout = QFormLayout()

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(config["temperature"])

        self.model_name = QLineEdit()
        self.model_name.setText(config["model_name"])

        params_layout.addRow("Temperature", self.temperature)
        params_layout.addRow("Model", self.model_name)

        params_widget.setLayout(params_layout)
        tabs.addTab(params_widget, "Parameters")

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_config(self):
        return {
            "system_prompt": self.system_prompt.toPlainText(),
            "temperature": self.temperature.value(),
            "model_name": self.model_name.text(),
        }


class MessageWidget(QFrame):
    def __init__(self, text="", is_user=True, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.message = QTextEdit()
        self.message.setReadOnly(True)
        self.message.setPlainText(text)
        self.message.setFrameStyle(QFrame.Shape.NoFrame)

        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border-radius: 10px;
                    margin: 5px 50px 5px 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border-radius: 10px;
                    margin: 5px 5px 5px 50px;
                }
            """)

        layout.addWidget(self.message)

    def append_text(self, text):
        cursor = self.message.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.message.setTextCursor(cursor)


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal AI")
        self.setMinimumSize(600, 800)

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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create scroll area for messages
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create widget to hold messages
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()

        scroll_area.setWidget(self.messages_widget)
        layout.addWidget(scroll_area)

        # Create typing indicator
        self.typing_indicator = TypingIndicator()
        self.typing_indicator.hide()
        self.messages_layout.addWidget(self.typing_indicator)

        # Create input area
        self.input_box = QTextEdit()
        self.input_box.setMaximumHeight(100)
        self.input_box.setPlaceholderText("Type your message here...")
        layout.addWidget(self.input_box)

        # Create send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        # # Add welcome message
        # self.add_message(
        #     "Welcome! Using Ollama with model: " + self.config["model_name"], False
        # )

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        # Configure LLM action
        config_action = QAction("Configure AI", self)
        config_action.triggered.connect(self.show_config_dialog)
        settings_menu.addAction(config_action)

        # Save/Load conversation actions
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_conversation)
        settings_menu.addAction(save_action)

        load_action = QAction("Load", self)
        load_action.triggered.connect(self.load_conversation)
        settings_menu.addAction(load_action)

    def load_config(self):
        try:
            with open(CONFIG_FILE_NAME, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "system_prompt": "You are a helpful AI assistant.",
                "temperature": 0.7,
                "model_name": "llama3.2",
            }

    def save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            json.dump(self.config, f, indent=4)

    def show_config_dialog(self):
        dialog = ConfigDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self.save_config()

    def save_conversation(self):
        file_name, _ = QFileDialog.getSaveFileName(
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
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Conversation", "", "JSON Files (*.json)"
        )
        if file_name:
            with open(file_name, "r") as f:
                conversation_data = json.load(f)

            # Clear current conversation
            for i in reversed(
                range(self.messages_layout.count() - 2)
            ):  # -2 for stretch and typing indicator
                widget = self.messages_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            # Load configuration
            self.config = conversation_data.get("config", self.config)

            # Load messages
            self.conversation_history = conversation_data.get("messages", [])
            for message in self.conversation_history:
                if message["role"] != "system":
                    self.add_message(
                        message["content"], is_user=(message["role"] == "user")
                    )

    def add_message(self, text, is_user=True):
        message = MessageWidget(text, is_user)
        insert_pos = (
            self.messages_layout.count()
        )  # Account for stretch and typing indicator
        self.messages_layout.insertWidget(insert_pos, message)
        return message

    def send_message(self):
        # Disable input while processing
        self.input_box.setEnabled(False)
        self.send_button.setEnabled(False)

        message_text = self.input_box.toPlainText().strip()
        self.input_box.clear()

        if message_text:
            # Add user message
            self.add_message(message_text, True)

            # Show typing indicator
            self.typing_indicator.start()

            # Create response widget with empty text
            response_widget = self.add_message("", False)

            # Start response generation in a separate thread
            thread = threading.Thread(
                target=self.generate_response, args=(message_text, response_widget)
            )
            thread.start()

    def generate_response(self, user_input, response_widget):
        try:
            # Add user message to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})

            print(self.conversation_history)

            # Generate streaming response using Ollama
            response_text = ""
            for response in ollama.chat(
                model=self.config["model_name"],
                messages=self.conversation_history,
                stream=True,
                options={"temperature": self.config["temperature"]},
            ):
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
            error_message += (
                f"2. The model '{self.config['model_name']}' is available\n"
            )
            error_message += "3. You can run 'ollama run modelname' in terminal"
            response_widget.append_text(error_message)

        finally:
            # Re-enable input in the main thread
            self.input_box.setEnabled(True)
            self.send_button.setEnabled(True)
            self.typing_indicator.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Arial", 10)
    app.setFont(font)

    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
