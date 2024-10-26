from PySide6 import QtWidgets
import ollama


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, character, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character configuration")
        self.setMinimumWidth(500)

        self.name = QtWidgets.QLineEdit()
        self.name.setText(character["name"])

        self.system_prompt = QtWidgets.QTextEdit()
        self.system_prompt.setPlainText(character["system_prompt"])
        self.system_prompt.setMinimumHeight(200)

        self.model = QtWidgets.QComboBox()
        installed_models = []
        for item in ollama.list()["models"]:
            installed_models.append(item["name"].split(":")[0])
        installed_models.sort()
        self.model.addItems(installed_models)
        i = self.model.findText(character["model"])
        if i >= 0:
            self.model.setCurrentIndex(i)
        else:
            self.model.addItem(character["model"])

        self.context_limit = QtWidgets.QSpinBox()
        self.context_limit.setRange(0, 1_000_000)
        self.context_limit.setSingleStep(1000)
        self.context_limit.setValue(character["context_limit"])

        self.temperature = QtWidgets.QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(character["temperature"])

        clayout = QtWidgets.QFormLayout()
        clayout.addRow("Name", self.name)
        clayout.addRow("System prompt", self.system_prompt)
        clayout.addRow("Model", self.model)
        clayout.addRow("Context Limit", self.context_limit)
        clayout.addRow("Temperature", self.temperature)

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

    def get_config(self):
        return {
            "name": self.name.text(),
            "system_prompt": self.system_prompt.toPlainText(),
            "model": self.model.currentText(),
            "context_limit": self.context_limit.value(),
            "temperature": self.temperature.value(),
        }
