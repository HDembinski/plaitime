from PySide6 import QtWidgets
import ollama
from pai.data_classes import Character
from typing import List


class ConfigDialog(QtWidgets.QDialog):
    conversation: List[str]

    def __init__(self, character: Character, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character configuration")
        self.setMinimumWidth(500)

        self.name = QtWidgets.QLineEdit()
        self.name.setText(character.name)

        self.prompt = QtWidgets.QTextEdit()
        self.prompt.setPlainText(character.prompt)
        self.prompt.setMinimumHeight(200)

        self.model = QtWidgets.QComboBox()
        installed_models = []
        for item in ollama.list()["models"]:
            installed_models.append(item["name"].split(":")[0])
        installed_models.sort()
        self.model.addItems(installed_models)
        i = self.model.findText(character.model)
        if i >= 0:
            self.model.setCurrentIndex(i)
        else:
            self.model.addItem(character.model)

        self.temperature = QtWidgets.QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(character.temperature)

        self.append_global_prompt = QtWidgets.QCheckBox()
        self.append_global_prompt.setChecked(character.append_global_prompt)

        self.clear_button = QtWidgets.QPushButton()
        self.clear_button.setCheckable(True)

        clayout = QtWidgets.QFormLayout()
        clayout.addRow("Name", self.name)
        clayout.addRow("Prompt", self.prompt)
        clayout.addRow("Model", self.model)
        clayout.addRow("Temperature", self.temperature)
        clayout.addRow("Append global prompt", self.append_global_prompt)
        clayout.addRow("Clear conversation", self.clear_button)

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

        self.conversation = character.conversation

    def result(self):
        return Character(
            name=self.name.text(),
            prompt=self.prompt.toPlainText(),
            model=self.model.currentText(),
            temperature=self.temperature.value(),
            append_global_prompt=self.append_global_prompt.is_checked(),
            conversation=[] if self.clear_button.isChecked() else self.conversation,
        )
