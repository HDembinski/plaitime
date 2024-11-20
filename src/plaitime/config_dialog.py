from PySide6 import QtWidgets, QtGui
import ollama
from .data_models import (
    ShortString,
    LongString,
    ModelString,
    FontString,
    ColorString,
)
from typing import Annotated
from annotated_types import Interval
from pydantic import BaseModel


class ColorButton(QtWidgets.QPushButton):
    _color: QtGui.QColor

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.set(QtGui.QColor.fromString(color))
        self.clicked.connect(self.choose)

    def set(self, color: QtGui.QColor):
        self._color = color
        self.setStyleSheet(f"background-color: {color.name()};")

    def choose(self):
        color = QtWidgets.QColorDialog.getColor(self._color, None, "Choose Color")
        if color.isValid():
            self.set(color)

    def get(self) -> str:
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

        vlayout = QtWidgets.QVBoxLayout(self)
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

    def result(self):
        d = {}
        for w, name in zip(self._widgets, self._model_cls.__annotations__):
            d[name] = get_widget_value(w)

        return self._model_cls.model_validate(d)


def generate_widget(
    field_type: Annotated[str | int | float, ...] | bool,
    value: str | int | float | bool,
):
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
    elif field_type is ColorString:
        w = ColorButton(value)
    elif field_type is FontString:
        w = QtWidgets.QFontComboBox()
        w.setCurrentFont(QtGui.QFont(value))
    else:
        # must be Annotated[...] when arriving here
        assert hasattr(field_type, "__metadata__")
        md = field_type.__metadata__[0]
        if md == "noconfig":
            w = None
        elif field_type.__origin__ is float:
            w = QtWidgets.QDoubleSpinBox()
            interval: Interval = md
            w.setRange(interval.ge, interval.le)
            w.setSingleStep(0.1)
            w.setDecimals(1)
            w.setValue(value)
        elif field_type.__origin__ is int:
            w = QtWidgets.QSpinBox()
            interval: Interval = md
            w.setRange(interval.ge, interval.le)
            w.setValue(value)
        else:
            assert False, f"{field_type} not implemented"
    return w


def get_widget_value(
    w: QtWidgets.QWidget | str | int | float | bool,
) -> str | int | float | bool:
    if isinstance(w, QtWidgets.QTextEdit):
        return w.toPlainText()
    if isinstance(w, QtWidgets.QLineEdit):
        return w.text()
    if isinstance(w, QtWidgets.QComboBox):
        return w.currentText()
    if isinstance(w, ColorButton):
        return w.get()
    if isinstance(w, QtWidgets.QFontComboBox):
        return w.font().family()
    if isinstance(w, QtWidgets.QCheckBox):
        return w.isChecked()
    if isinstance(w, QtWidgets.QDoubleSpinBox | QtWidgets.QSpinBox):
        return w.value()
    if isinstance(w, QtWidgets.QWidget):
        assert False, f"{w} not implement"
    return w
