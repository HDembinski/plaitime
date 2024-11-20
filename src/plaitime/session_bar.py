from PySide6 import QtWidgets, QtCore
from .util import get_session_names


class SessionBar(QtWidgets.QWidget):
    sessionChanged = QtCore.Signal(str)
    context_size: int = 0

    def __init__(self, parent=None):
        super().__init__(parent)

        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.setSizePolicy(size_policy)

        self.session = QtWidgets.QComboBox(self)
        self.session.setSizePolicy(size_policy)
        self.session.setMinimumWidth(200)
        self.session.currentTextChanged.connect(self.sessionChanged)

        self.clipboard_button = QtWidgets.QPushButton("Clipboard")
        self.num_token = QtWidgets.QLabel(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.session)
        layout.addWidget(self.clipboard_button)
        layout.addWidget(self.num_token)
        layout.setContentsMargins(0, 3, 5, 0)

    def set_session_manually(self, name: str):
        names = get_session_names()
        if name not in names:
            names.append(name)
        names.sort()
        self.session.blockSignals(True)
        self.session.clear()
        self.session.addItems(names)
        self.session.setCurrentText(name)
        self.session.blockSignals(False)

    def set_context_size(self, n: int):
        self.context_size = n

    def set_num_token(self, num: int):
        if num < 0:
            text = ""
        else:
            k = 1024
            text = f"{num/k:.1f} (est) | {self.context_size/k:.0f} k token"
        self.num_token.setText(text)
