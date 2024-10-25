import sys

from PySide6 import QtGui, QtWidgets

from pai.chat_window import ChatWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Set application-wide font
    font = QtGui.QFont("Arial", 10)
    app.setFont(font)

    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
