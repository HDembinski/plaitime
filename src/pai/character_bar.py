from PySide6 import QtWidgets
from pai import CHARACTER_DIRECTORY
import json


class CharacterBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        self.setSizePolicy(size_policy)

        self.config_button = QtWidgets.QPushButton("Configure")
        self.character_selector = QtWidgets.QComboBox()
        self.new_button = QtWidgets.QPushButton("New character")
        self.clipboard_button = QtWidgets.QPushButton("Clipboard")
        self.num_token = QtWidgets.QProgressBar()
        self.num_token.setFormat("%v token (est.)")
        self.num_token.setMinimum(0)
        self.num_token.setSizePolicy(size_policy)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.config_button)
        layout.addWidget(self.character_selector)
        layout.addWidget(self.new_button)
        layout.addWidget(self.clipboard_button)
        layout.addWidget(self.num_token)
        self.setLayout(layout)

    def set_character_manually(self, new_name):
        names = get_character_names()
        if new_name not in names:
            names.append(new_name)
        names.sort()
        self.character_selector.blockSignals(True)
        self.character_selector.clear()
        for name in names:
            self.character_selector.addItem(name)
        self.character_selector.setCurrentText(new_name)
        self.character_selector.blockSignals(False)

    def current_character(self):
        return self.character_selector.currentText()

    def update_num_token(self, num: int, size: int):
        self.num_token.setMaximum(size)
        self.num_token.setValue(max(num, 0))
        self.num_token.setDisabled(num < 0)


def get_character_names():
    names = []
    for fn in CHARACTER_DIRECTORY.glob("*.json"):
        with open(fn) as f:
            name = json.load(f)["name"]
            names.append(name)
    return names
