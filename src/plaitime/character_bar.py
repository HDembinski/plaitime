from PySide6 import QtWidgets
from .util import get_character_names


class CharacterBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setSizePolicy(size_policy)

        self.character_selector = QtWidgets.QComboBox()
        self.character_selector.setSizePolicy(size_policy)
        self.clipboard_button = QtWidgets.QPushButton("Clipboard")
        self.num_token = QtWidgets.QLabel()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.character_selector)
        layout.addWidget(self.clipboard_button)
        layout.addWidget(self.num_token)
        self.setLayout(layout)

        self.context_size = 0

    def set_character_manually(self, name: str):
        names = get_character_names()
        if name not in names:
            names.append(name)
        names.sort()
        self.character_selector.blockSignals(True)
        self.character_selector.clear()
        self.character_selector.addItems(names)
        self.character_selector.setCurrentText(name)
        self.character_selector.blockSignals(False)

    def set_context_size(self, n: int):
        self.context_size = n

    def set_num_token(self, num: int):
        if num < 0:
            text = ""
        else:
            k = 1024
            text = f"{num/k:.1f} (est) | {self.context_size/k:.0f} k token"
        self.num_token.setText(text)
