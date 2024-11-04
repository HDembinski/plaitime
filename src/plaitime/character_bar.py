from PySide6 import QtWidgets


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
        self.summary_button = QtWidgets.QPushButton("Summary")
        self.num_token = QtWidgets.QLabel()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.config_button)
        layout.addWidget(self.character_selector)
        layout.addWidget(self.new_button)
        layout.addWidget(self.clipboard_button)
        layout.addWidget(self.summary_button)
        layout.addWidget(self.num_token)
        self.setLayout(layout)

    def set_character_manually(self, names: list[str], new_name: str):
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
        if num < 0:
            text = ""
        else:
            k = 1024
            text = f"{num/k:.1f} (est) | {size/k:.0f} k token"
        self.num_token.setText(text)
