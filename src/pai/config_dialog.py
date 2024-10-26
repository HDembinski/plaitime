from PySide6 import QtWidgets
import ollama


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LLM Configuration")
        self.setMinimumWidth(500)

        tabs = QtWidgets.QTabWidget()

        # System Prompt Tab
        system_prompt_widget = QtWidgets.QWidget()
        system_prompt_layout = QtWidgets.QVBoxLayout()

        self.system_prompt = QtWidgets.QTextEdit()
        self.system_prompt.setPlainText(config["system_prompt"])
        self.system_prompt.setMinimumHeight(200)

        system_prompt_layout.addWidget(QtWidgets.QLabel("System Prompt"))
        system_prompt_layout.addWidget(self.system_prompt)
        system_prompt_widget.setLayout(system_prompt_layout)
        tabs.addTab(system_prompt_widget, "System Prompt")

        # Model Parameters Tab
        params_widget = QtWidgets.QWidget()
        params_layout = QtWidgets.QFormLayout()

        self.model = QtWidgets.QComboBox()
        installed_models = []
        for item in ollama.list()["models"]:
            installed_models.append(item["name"].split(":")[0])
        installed_models.sort()
        self.model.addItems(installed_models)
        i = self.model.findText(config["model"])
        if i >= 0:
            self.model.setCurrentIndex(i)
        else:
            self.model.addItem(config["model"])

        self.context_limit = QtWidgets.QSpinBox()
        self.context_limit.setRange(0, 1_000_000)
        self.context_limit.setSingleStep(1000)
        self.context_limit.setValue(config["context_limit"])

        self.temperature = QtWidgets.QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(config["temperature"])

        params_layout.addRow("Model", self.model)
        params_layout.addRow("Context Limit", self.context_limit)
        params_layout.addRow("Temperature", self.temperature)

        params_widget.setLayout(params_layout)
        tabs.addTab(params_widget, "Parameters")

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_config(self):
        return {
            "system_prompt": self.system_prompt.toPlainText(),
            "model": self.model.currentText(),
            "context_limit": self.context_limit.value(),
            "temperature": self.temperature.value(),
        }
