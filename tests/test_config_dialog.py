from plaitime.data_models import Character, Settings
from plaitime.config_dialog import ConfigDialog
import pytest
from PySide6 import QtWidgets

app = QtWidgets.QApplication([])


@pytest.mark.parametrize("model", (Character(), Settings()))
def test_config_dialog(model):
    c = ConfigDialog(model)
    assert c.result() == model
