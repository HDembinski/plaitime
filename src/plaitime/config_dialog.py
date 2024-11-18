from PySide6 import QtWidgets, QtGui
import ollama
from .data_models import (
    ShortString,
    LongString,
    ModelString,
    Color,
)
from typing import Annotated, Any
from annotated_types import Interval
from pydantic import BaseModel


class ColorButton(QtWidgets.QPushButton):
    _color: QtGui.QColor

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.set_color(QtGui.QColor.fromString(color))
        self.clicked.connect(self.choose_color)

    def set_color(self, color):
        self._color = color
        self.setStyleSheet(f"background-color: {color.name()};")

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(self._color, self, "Choose Color")
        if color.isValid():
            self.set_color(color)

    def get_color(self):
        return self._color.name()


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, model: BaseModel, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Configuration")
        self.setMinimumWidth(500)
        self._model_cls = type(model)
        self._widgets = []

        clayout = QtWidgets.QFormLayout()
        for field_name, field_type in model.__annotations__.items():
            value = getattr(model, field_name)
            widget = generate_widget(field_type, value)
            if widget is not None:
                clayout.addRow(field_name.replace("_", " ").capitalize(), widget)
                self._widgets.append(widget)
            else:
                self._widgets.append(value)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(clayout)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        vlayout.addWidget(button_box)
        self.setLayout(vlayout)

    def result(self):
        d = {}
        for w, name in zip(self._widgets, self._model_cls.__annotations__):
            d[name] = get_widget_value(w)

        return self._model_cls.model_validate(d)


def generate_widget(field_type: Annotated, value: Any):
    if field_type is bool:
        w = QtWidgets.QCheckBox()
        w.setChecked(value)
    elif field_type is ShortString:
        w = QtWidgets.QLineEdit()
        w.setText(value)
    elif field_type is LongString:
        w = QtWidgets.QTextEdit()
        w.setPlainText(value)
    elif field_type is ModelString:
        models = []
        for item in ollama.list()["models"]:
            models.append(item["name"])
        w = QtWidgets.QComboBox()
        w.addItems(sorted(models))
        w.setCurrentText(value)
    elif field_type is Color:
        w = ColorButton(value)
    elif field_type.__metadata__[0] == "noconfig":
        w = None
    elif field_type.__origin__ is float:
        w = QtWidgets.QDoubleSpinBox()
        interval: Interval = field_type.__metadata__[0]
        w.setRange(interval.gt, interval.lt)
        w.setDecimals(1)
        w.setValue(value)
    else:
        assert False, f"{field_type} not implemented"
    return w


def get_widget_value(
    w: QtWidgets.QWidget | str | float | bool | int,
) -> str | float | bool:
    if isinstance(w, QtWidgets.QTextEdit):
        return w.toPlainText()
    if isinstance(w, QtWidgets.QLineEdit):
        return w.text()
    if isinstance(w, QtWidgets.QComboBox):
        return w.currentText()
    if isinstance(w, ColorButton):
        return w.get_color()
    if isinstance(w, QtWidgets.QCheckBox):
        return w.isChecked()
    if isinstance(w, QtWidgets.QDoubleSpinBox):
        return w.value()
    if isinstance(w, QtWidgets.QWidget):
        assert False, f"{w} not implement"
    return w
