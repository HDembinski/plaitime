from PySide6 import QtWidgets, QtCore
from .message_widget import MessageWidget


class ChatWidget(QtWidgets.QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.verticalScrollBar().rangeChanged.connect(
            lambda _, vmax: self.verticalScrollBar().setValue(vmax)
        )
        layout = QtWidgets.QVBoxLayout()
        layout.addStretch(1)
        self.scrollable_content = QtWidgets.QWidget()
        self.scrollable_content.setLayout(layout)
        self.setWidget(self.scrollable_content)

    def add(self, role: str, content: str):
        mw = MessageWidget(role, content)
        self.scrollable_content.layout().addWidget(mw)
        return mw

    def get_messages(self) -> list[MessageWidget]:
        return self.scrollable_content.children()[1:]

    def clear(self):
        for child in self.get_messages():
            child.setParent(None)
            child.deleteLater()
