from PySide6 import QtWidgets
import ollama
from .data_models import Character, Memory


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, character: Character, memory: Memory, *, parent=None):
        super().__init__(parent)

        self.memory = memory

        self.setWindowTitle("Character configuration")
        self.setMinimumWidth(500)

        self.name = QtWidgets.QLineEdit()
        self.name.setText(character.name)

        self.prompt = QtWidgets.QTextEdit()
        self.prompt.setPlainText(character.prompt)
        self.prompt.setAcceptRichText(False)
        self.prompt.setMinimumHeight(200)

        self.model = QtWidgets.QComboBox()
        installed_models = []
        for item in ollama.list()["models"]:
            installed_models.append(item["name"])
        installed_models.sort()
        self.model.addItems(installed_models)
        i = self.model.findText(character.model)
        if i >= 0:
            self.model.setCurrentIndex(i)
        else:
            self.model.addItem(character.model)

        self.temperature = QtWidgets.QDoubleSpinBox()
        self.temperature.setRange(0, 2.0)
        self.temperature.setDecimals(1)
        self.temperature.setValue(character.temperature)

        self.save_conversation = QtWidgets.QCheckBox()
        self.save_conversation.setChecked(character.save_conversation)

        self.clear_conversation = QtWidgets.QCheckBox()
        self.clear_conversation.setChecked(False)

        self.delete_character = QtWidgets.QCheckBox()

        clayout = QtWidgets.QFormLayout()
        clayout.addRow("Name", self.name)
        clayout.addRow("Prompt", self.prompt)
        clayout.addRow("Model", self.model)
        clayout.addRow("Temperature", self.temperature)
        clayout.addRow("Save conversation", self.save_conversation)
        clayout.addRow("Clear conversation", self.clear_conversation)
        clayout.addRow("Delete character", self.delete_character)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(clayout)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        vlayout.addWidget(button_box)
        self.setLayout(vlayout)

    def result(self):
        if self.delete_character.isChecked():
            return self.name.text()
        else:
            memory = self.memory
            if self.clear_conversation.isChecked():
                memory.messages = []

            return (
                Character(
                    name=self.name.text(),
                    prompt=self.prompt.toPlainText(),
                    model=self.model.currentText(),
                    temperature=self.temperature.value(),
                    save_conversation=self.save_conversation.isChecked(),
                ),
                memory,
            )
