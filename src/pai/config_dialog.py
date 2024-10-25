from PySide6 import QtWidgets


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
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

        self.temperature = QtWidgets.QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(config["temperature"])

        self.model_name = QtWidgets.QLineEdit()
        self.model_name.setText(config["model_name"])

        params_layout.addRow("Temperature", self.temperature)
        params_layout.addRow("Model", self.model_name)

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
            "temperature": self.temperature.value(),
            "model_name": self.model_name.text(),
        }
