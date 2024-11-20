import logging

import ollama
from ollama import ResponseError
from PySide6 import QtCore, QtGui, QtWidgets

from . import (
    SETTINGS_FILE_NAME,
    CHARACTER_DIRECTORY,
    MEMORY_DIRECTORY,
    STORY_EXTRACTION_PROMPT,
    CONTEXT_MARGIN_FRACTION,
    CHARACTERS_PER_TOKEN,
)
from .character_bar import CharacterBar
from .config_dialog import ConfigDialog
from .data_models import Settings, Character, Memory, Message
from .generator import Chat, Generate, GeneratorThread
from .chat_widget import ChatWidget
from .util import estimate_num_tokens, get_character_names
from .io import load, save, lock_and_load, save_and_release, rename

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    __slots__ = (
        "settings",
        "character",
        "generator",
        "cancel_mode",
        "context_size",
        "chat_widget",
        "updateCharacterName",
        "updateContextSize",
    )

    settings: Settings
    character: Character
    generator: GeneratorThread | None
    cancel_mode: str
    context_size: int
    chat_widget: ChatWidget
    character_bar: CharacterBar

    sendContextSize = QtCore.Signal(int)
    sendNumToken = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load(SETTINGS_FILE_NAME, Settings)
        self.character = Character()
        self.generator = None
        self.cancel_mode = "rewind"

        self.setWindowTitle("Plaitime")
        self.setMinimumSize(600, 500)
        self.setGeometry(*self.settings.geometry)

        menu_bar = self.menuBar()
        settings_action = QtGui.QAction("Settings", self)
        settings_action.triggered.connect(self.configure_settings)
        menu_bar.addAction(settings_action)
        char_menu = menu_bar.addMenu("Character")
        char_conf_action = char_menu.addAction("Configure")
        char_new_action = char_menu.addAction("New")
        char_del_action = char_menu.addAction("Delete")
        char_conf_action.triggered.connect(self.configure_character)
        char_new_action.triggered.connect(self.new_character)
        char_del_action.triggered.connect(self.delete_character)

        self.character_bar = CharacterBar(self)
        menu_bar.setCornerWidget(self.character_bar)
        self.character_bar.character_selector.currentTextChanged.connect(
            self.switch_character
        )
        self.character_bar.clipboard_button.clicked.connect(self.copy_to_clipboard)
        self.sendContextSize.connect(self.character_bar.set_context_size)
        self.sendNumToken.connect(self.character_bar.set_num_token)

        self.make_chat_widget()
        self.setCentralWidget(self.chat_widget)

        # Must be at the end
        self.load_character(self.settings.character)

    def make_chat_widget(self, reload: bool = False):
        if reload:
            # save messages
            messages = self.chat_widget.get_messages()
            # delete old chat widget
            self.chat_widget.setParent(None)
            self.chat_widget.deleteLater()

        self.chat_widget = ChatWidget(self.settings, self)
        self.chat_widget.sendMessage.connect(self.generate_response)
        self.chat_widget.sendSummaryClick.connect(self.generate_summary)
        self.setCentralWidget(self.chat_widget)

        if reload:
            # reload messages
            self.chat_widget.load_messages(messages)

    def save_settings(self):
        self.settings.character = self.character.name
        g = self.geometry()
        self.settings.geometry = (g.left(), g.top(), g.width(), g.height())
        save(self.settings, SETTINGS_FILE_NAME)

    def load_character(self, name: str):
        logger.info(f"loading character {name!r}")
        names = get_character_names()
        if not name and names:
            name = names[0]
        try:
            self.character = lock_and_load(
                CHARACTER_DIRECTORY / f"{name}.json", Character
            )
        except IOError:
            self.character = Character()
        self.update_context_size()
        self.character_bar.set_character_manually(self.character.name)
        if self.character.save_conversation:
            memory = load(MEMORY_DIRECTORY / f"{self.character.name}.json", Memory)
        else:
            memory = Memory()
        self.chat_widget.load_messages(memory.messages)
        num = estimate_num_tokens(memory.messages, self.character.prompt)
        self.sendNumToken.emit(num)
        self.warmup_model()

    def save_character(self):
        c = self.character
        logger.info(f"saving character {c.name!r}")
        try:
            save_and_release(c, CHARACTER_DIRECTORY / f"{c.name}.json")
        except ValueError:
            logger.warning("cannot save character which is locked by another instance")
            return

        if c.save_conversation:
            widgets = self.chat_widget.get_messages()
            messages = [Message(role=w.role, content=w.content) for w in widgets]
            user_text = self.chat_widget.get_user_text()
            if user_text:
                messages.append(Message(role="user", content=user_text))
            if messages:
                memory = Memory(messages=messages)
                save(memory, MEMORY_DIRECTORY / f"{c.name}.json")
                return
        # remove file, if there is nothing to save
        path = MEMORY_DIRECTORY / f"{c.name}.json"
        path.unlink(missing_ok=True)

    def rename_character(self, old_name: str, new_name: str):
        logger.info(f"renaming character from {old_name!r} to {new_name!r}")
        files = [
            CHARACTER_DIRECTORY / f"{old_name}.json",
            CHARACTER_DIRECTORY / f"{old_name}.lock",
            MEMORY_DIRECTORY / f"{old_name}.json",
        ]
        for f in files:
            if f.exists():
                rename(f, new_name)

    def save_all(self):
        self.save_settings()
        self.save_character()

    @QtCore.Slot()
    def configure_settings(self):
        dialog = ConfigDialog(self.settings, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.settings = dialog.result()
            # colors changed, we need to reload the web view
            self.make_chat_widget(reload=True)

    @QtCore.Slot()
    def configure_character(self, new_character: bool = False):
        dialog = ConfigDialog(self.character, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            character: Character = dialog.result()
            if not new_character and self.character.name != character.name:
                self.rename_character(self.character.name, character.name)
            self.character = character
            self.character_bar.set_character_manually(self.character.name)
            self.update_context_size()
            num = estimate_num_tokens(
                self.chat_widget.get_messages(), self.character.prompt
            )
            self.sendNumToken.emit(num)
            self.warmup_model()

    @QtCore.Slot()
    def new_character(self):
        self.save_character()
        # this is important, otherwise the old character is deleted in configure_character
        self.character = Character()
        self.chat_widget.load_messages([])
        self.configure_character(new_character=True)

    @QtCore.Slot()
    def delete_character(self):
        name = self.character.name
        logger.info(f"deleting character {name}")
        for path in (
            CHARACTER_DIRECTORY / f"{name}.json",
            CHARACTER_DIRECTORY / f"{name}.lock",
            MEMORY_DIRECTORY / f"{name}.json",
        ):
            path.unlink(missing_ok=True)
        self.load_character("")

    def update_context_size(self):
        size = get_context_size(self.character.model)
        self.context_size = size
        self.sendContextSize.emit(size)

    @QtCore.Slot(str)
    def switch_character(self, name):
        if name == self.character.name:
            logger.warning(f"trying to switching same character {name}")
            return
        logger.info(f"switching character to {name}")
        self.save_character()
        self.load_character(name)

    def rewind(self, partial=True):
        self.cancel_generator()
        if self.cancel_mode == "rewind":
            self.chat_widget.rewind(partial)

    @QtCore.Slot()
    def generator_finished(self):
        # trim excess whitespace
        messages = self.chat_widget.get_messages()
        messages[-1].set_content(messages[-1].content.strip())

        self.chat_widget.enable()
        self.generator = None
        num = estimate_num_tokens(
            self.chat_widget.get_messages(), self.character.prompt
        )
        self.sendNumToken.emit(num)

    def generate_response(self):
        self.chat_widget.disable()
        self.save_character()

        prompt = self.character.prompt

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        window = []
        num_token = len(prompt) / CHARACTERS_PER_TOKEN
        for w in reversed(self.chat_widget.get_messages()):
            w.unmark()
            window.append({"role": w.role, "content": w.content})
            num_token += len(w.content) / CHARACTERS_PER_TOKEN
            if num_token > self.context_size * (1 - CONTEXT_MARGIN_FRACTION):
                break
        assert len(window) > 0
        assert w.content == window[-1]["content"]
        w.mark()
        window.append({"role": "system", "content": prompt})
        window.reverse()

        self.cancel_generator(wait=True)
        self.generator = Chat(
            self.character.model, window, temperature=self.character.temperature
        )
        mw = self.chat_widget.add("assistant", "")
        self.generator.nextChunk.connect(mw.add_chunk)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generator_finished)
        self.cancel_mode = "rewind"
        self.generator.start()

    def get_dialog_as_text(self):
        messages = self.chat_widget.get_messages()
        text = self.character.prompt + "\n\n".join(
            f"{m.role.capitalize()}:\n{m.content}" for m in messages
        )
        return text

    @QtCore.Slot()
    def copy_to_clipboard(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(self.get_dialog_as_text())

    @QtCore.Slot()
    def generate_summary(self):
        prompt = STORY_EXTRACTION_PROMPT.format(self.get_dialog_as_text())

        self.cancel_generator(wait=True)
        self.cancel_mode = "cancel"
        self.generator = Generate(
            self.character.model,
            prompt=prompt,
            temperature=0.1,
        )
        self.generator.nextChunk.connect(self.chat_widget.add_user_text)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generate_summary_finished)
        self.generator.start()

    @QtCore.Slot(str)
    def show_error_message(self, message: str):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.exec()

    @QtCore.Slot()
    def generate_summary_finished(self):
        self.generator = None
        self.chat_widget.enable()

    def cancel_generator(self, *, wait=False):
        self.cancel_mode = "rewind"
        if self.generator and self.generator.isRunning():
            logger.info("Generator is running, interrupting...")
            self.generator.interrupt = True
            if wait:
                logger.info("Waiting for generator to finish...")
                self.generator.wait()
                self.generator = None

    def keyPressEvent(self, event):
        key = event.key()
        mod = event.modifiers()
        if key == QtCore.Qt.Key.Key_Escape:
            self.rewind(not (mod & QtCore.Qt.KeyboardModifier.ShiftModifier))
        elif key == QtCore.Qt.Key.Key_Return:
            self.chat_widget.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def warmup_model(self):
        if self.generator and self.generator.isRunning():
            return

        self.generator = Generate(self.character.model, "")

        @QtCore.Slot()
        def finished():
            self.generator = None

        self.generator.finished.connect(finished)
        self.generator.start()


def get_context_size(model):
    try:
        d = ollama.show(model)["model_info"]
        for key in d:
            if "context_length" in key:
                return d[key]
        raise RuntimeError("context_length not found")
        # model was removed
    except ResponseError:
        return 0
