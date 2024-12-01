from PySide6 import QtWidgets, QtGui
import ollama
from annotated_types import Interval
from pydantic import BaseModel
from pydantic.fields import FieldInfo


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

        widget, self.result = make_widget_and_getter(None, model)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addWidget(widget)
        vlayout.addWidget(button_box)


def make_widget_and_getter(
    field_info: FieldInfo | None,
    value: BaseModel | str | int | float | bool,
):
    if field_info is None or isinstance(value, BaseModel):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(w)
        gis = []
        for name, info in value.model_fields.items():
            wi, gi = make_widget_and_getter(info, getattr(value, name))
            if wi:
                layout.addRow(name.replace("_", " ").capitalize(), wi)
            gis.append(gi)

        def g():
            return value.model_validate(
                {ni: gi() for (ni, gi) in zip(value.model_fields, gis)}
            )

        return w, g

    field_type = field_info.annotation
    metadata = field_info.metadata
    if metadata == ["noconfig"]:
        w = None

        def g():
            return value
    elif field_type is bool and not metadata:
        w = QtWidgets.QCheckBox()
        w.setChecked(value)
        g = w.isChecked
    elif field_type is str:
        if not metadata:
            w = QtWidgets.QLineEdit()
            w.setText(value)

            def g():
                return w.text().strip()
        elif metadata == ["long"]:
            w = QtWidgets.QTextEdit()
            w.setAcceptRichText(False)
            w.setPlainText(value)
            g = w.toPlainText
        elif metadata == ["model"]:
            models = []
            for item in ollama.list().models:
                models.append(item.model)
            w = QtWidgets.QComboBox()
            w.addItems(sorted(models))
            w.setCurrentText(value)
            g = w.currentText
        elif metadata == ["color"]:
            w = ColorButton(value)
            g = w.get
        elif metadata == ["font"]:
            w = QtWidgets.QFontComboBox()
            w.setCurrentFont(QtGui.QFont(value))

            def g():
                return w.currentFont().family()
    else:
        assert metadata, f"{field_info!r}"
        if field_type is float:
            w = QtWidgets.QDoubleSpinBox()
            interval: Interval = metadata[0]
            w.setRange(interval.ge, interval.le)
            w.setSingleStep(0.1)
            w.setDecimals(1)
            w.setValue(value)
            g = w.value
        elif field_type is int:
            w = QtWidgets.QSpinBox()
            interval: Interval = metadata[0]
            w.setRange(interval.ge, interval.le)
            w.setValue(value)
            g = w.value
        else:
            assert False, f"{field_type} not implemented"
    return w, g
