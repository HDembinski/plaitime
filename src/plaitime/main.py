import logging
import sys
from importlib.resources import files

from PySide6 import QtGui, QtWidgets

from .main_window import MainWindow


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

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
