from PySide6 import QtWidgets, QtCore, QtGui
from plaitime.data_models import Character
from plaitime.config_dialog import ConfigDialog


class Model(QtCore.QAbstractListModel):
    def __init__(self, characters: list[Character], parent=None):
        super().__init__(parent)
        self.characters = characters

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.characters)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.QModelRoleData = QtCore.Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid() or (index.row() >= self.rowCount()):
            return None

        character = self.characters[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.format_character(character)
        return None

    def format_character(self, character: Character) -> str:
        return f"""
<style>
</style>
<h2>{character.name}</h2>
<table>
    <tr><th>Eyes</th> <td>{character.eyes}</td></tr>
    <tr><th>Hair</th> <td>{character.hair}</td></tr>
    <tr><th>Age</th> <td>{character.age}</td></tr>
    <tr><th>Clothing</th> <td>{character.clothing}</td></tr>
    <tr><th>Occupation</th> <td>{character.occupation}</td></tr>
    <tr><th>Weapons</th> <td>{character.weapons.replace("\n", "<br/>")}</td></tr>
    <tr><th>Abilities</th> <td>{character.abilities.replace("\n", "<br/>")}</td></tr>
    <tr><th>Notes</th> <td>{character.notes.replace("\n", "<br/>")}</td></tr>
</table>
"""


class HTMLDelegate(QtWidgets.QStyledItemDelegate):
    def make_text_doc(self, index, option):
        html = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        doc = QtGui.QTextDocument()
        text_option = QtGui.QTextOption()
        text_option.setWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        doc.setDefaultTextOption(text_option)
        doc.setTextWidth(option.rect.width())
        doc.setHtml(html)
        return doc

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ):
        # draw standard highlighting for selected items
        super().paint(painter, option, QtCore.QModelIndex())

        doc = self.make_text_doc(index, option)

        painter.save()
        painter.translate(option.rect.topLeft())
        content_rect = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        doc.drawContents(painter, content_rect)
        painter.restore()

    def sizeHint(
        self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex
    ):
        doc = self.make_text_doc(index, option)
        return doc.size().toSize()


class CharacterWidget(QtWidgets.QWidget):
    generateClicked = QtCore.Signal()

    def __init__(self, characters: list[Character], parent=None):
        super().__init__(parent)

        self.view = QtWidgets.QListView(self)
        self.view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.MultiSelection
        )
        self.model = Model(characters, self)
        self.view.setModel(self.model)
        self.view.setItemDelegate(HTMLDelegate())
        self.view.doubleClicked.connect(self.edit_character)

        generate_button = QtWidgets.QPushButton("Generate", self)
        new_button = QtWidgets.QPushButton("New character", self)
        delete_button = QtWidgets.QPushButton("Delete character(s)", self)
        generate_button.clicked.connect(self.generateClicked)
        new_button.clicked.connect(self.new_character)
        delete_button.clicked.connect(self.delete_characters)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.view)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(generate_button)
        button_layout.addWidget(new_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

    def setFont(self, font: QtGui.QFont):
        self.view.setFont(font)

    def edit_character(self, index: QtCore.QModelIndex):
        i = index.row()
        character = self.characters[i]
        dialog = ConfigDialog(character, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.characters[i] = dialog.result()
            self.model.layoutChanged.emit()

    def new_character(self):
        dialog = ConfigDialog(Character(name=""), self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.characters.append(dialog.result())
            self.model.layoutChanged.emit()

    def delete_characters(self):
        keep = set(range(len(self.characters))) - set(
            index.row() for index in self.view.selectedIndexes()
        )
        self.characters = [self.characters[i] for i in keep]
        self.model.layoutChanged.emit()

    def integrate(self, characters: list[Character] | None):
        if not characters:
            return

        name_map = {c.name: i for i, c in enumerate(self.characters)}
        for new in characters:
            i = name_map.get(new.name)
            if i is None:
                self.characters.append(new)
            else:
                old = self.characters[i]
                dnew = new.model_dump()
                for key, new_val in dnew.items():
                    old_val = getattr(old, key)
                    if old_val and new_val:
                        setattr(old, key, f"{old_val}; {new_val}")
                    elif new_val:
                        setattr(old, key, new_val)
                    else:
                        assert new_val == ""
                self.characters[i] = old

        self.model.layoutChanged.emit()

    @property
    def characters(self) -> list[Character]:
        return self.model.characters

    @characters.setter
    def characters(self, value: list[Character]):
        self.model.characters = value

    def add_chunk(self, chunk: str):
        print(chunk, end="")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    # Create a list of Character objects
    characters = [
        Character(
            name="Aragorn",
            eyes="Grey",
            hair="Dark",
            age="87",
            clothing="Ranger outfit",
            occupation="Ranger/King",
            weapons="Sword, Bow",
            abilities="Leadership, Combat skills",
            notes="Heir to the throne of Gondor",
        ),
        Character(
            name="Gandalf",
            eyes="Blue",
            hair="White",
            age="Unknown",
            clothing="Wizard robes",
            occupation="Wizard",
            weapons="Staff, Sword",
            abilities="Magic, Wisdom",
            notes="Known as Gandalf the Grey, later Gandalf the White",
        ),
    ]

    # Instantiate the main widget
    widget = CharacterWidget(characters)
    widget.show()

    sys.exit(app.exec())
