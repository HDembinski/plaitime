from PySide6 import QtWidgets
from pai import CHARACTER_DIRECTORY


class TopBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.config_button = QtWidgets.QPushButton("Configure")
        self.character_selector = QtWidgets.QComboBox()
        self.new_button = QtWidgets.QPushButton("Add character")
        self.clear_button = QtWidgets.QPushButton("Clear history")
        self.num_token = QtWidgets.QLabel()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.config_button)
        layout.addWidget(self.character_selector)
        layout.addWidget(self.new_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.num_token)
        self.setLayout(layout)

        self.update_num_token(0)

    def update(self, current_name):
        self.character_selector.blockSignals(True)
        names = [f.stem for f in CHARACTER_DIRECTORY.glob("*.json")]
        if current_name not in names:
            names.append(current_name)
        names.sort()
        self.character_selector.clear()
        for name in names:
            self.character_selector.addItem(name)
        self.character_selector.setCurrentText(current_name)
        self.character_selector.blockSignals(False)

    def current_character(self):
        return self.character_selector.currentText()

    def update_num_token(self, num):
        self.num_token.setText(f"{num:.0f} token")
