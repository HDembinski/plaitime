import sys

from PySide6 import QtGui, QtWidgets

from .chat_window import ChatWindow


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Set application-wide font
    font = QtGui.QFont("Arial", 10)
    app.setFont(font)

    window = ChatWindow()
    window.show()
    app.lastWindowClosed.connect(window.save_all)
    sys.exit(app.exec())
