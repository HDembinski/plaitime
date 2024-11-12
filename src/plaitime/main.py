import sys

from PySide6 import QtGui, QtWidgets
from importlib.resources import files

from .main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Set application-wide font
    font = QtGui.QFont("Arial", 11)
    app.setFont(font)

    window = MainWindow()

    icon_path = files("plaitime").joinpath("assets").joinpath("plaitime.png")
    icon = QtGui.QIcon(str(icon_path))

    window.setWindowIcon(icon)
    window.show()

    app.lastWindowClosed.connect(window.save_all)
    sys.exit(app.exec())
