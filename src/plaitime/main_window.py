import logging

import ollama
from ollama import ResponseError
from PySide6 import QtCore, QtGui, QtWidgets

from . import (
    SETTINGS_FILE_NAME,
    SESSION_DIRECTORY,
    MEMORY_DIRECTORY,
    CHARACTERS_PER_TOKEN,
    STORY_PROMPT,
    CHARACTERS_PROMPT,
    WORLD_PROMPT,
)
from .session_bar import SessionBar
from .config_dialog import ConfigDialog
from .data_models import Settings, Session, Memory, Message, CharacterList
from .generator import Chat, Generate, GenerateData
from .chat_widget import ChatWidget
from .util import estimate_num_tokens, get_session_names
from .io import load, save, lock_and_load, save_and_release, rename
from .text_edit import TextEditor
from .character_widget import CharacterWidget

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    settings: Settings
    session: Session
    generator: Chat | Generate | GenerateData | None
    cancel_mode: str

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load(SETTINGS_FILE_NAME, Settings)
        self.session = Session()
        self.generator = None
        self.cancel_mode = "rewind"

        self.setWindowTitle("Plaitime")
        self.setMinimumSize(600, 500)
        self.setGeometry(*self.settings.geometry)

        menu_bar = self.menuBar()
        settings_action = QtGui.QAction("Settings", self)
        settings_action.triggered.connect(self.configure_settings)
        menu_bar.addAction(settings_action)
        session_menu = menu_bar.addMenu("Session")
        char_conf_action = session_menu.addAction("Configure")
        char_new_action = session_menu.addAction("New")
        char_del_action = session_menu.addAction("Delete")
        char_conf_action.triggered.connect(self.configure_session)
        char_new_action.triggered.connect(self.new_session)
        char_del_action.triggered.connect(self.delete_session)

        self.session_bar = SessionBar(self)
        menu_bar.setCornerWidget(self.session_bar)
        self.session_bar.sessionChanged.connect(self.switch_session)
        self.session_bar.clipboard_button.clicked.connect(self.copy_to_clipboard)

        font = self.settings.font.qfont()
        self.chat_widget = ChatWidget(
            self.settings.colors,
            self,
        )
        self.chat_widget.setFont(font)
        self.chat_widget.sendMessage.connect(self.generate_response)
        self.story_widget = TextEditor(self)
        self.story_widget.setFont(font)
        self.story_widget.generateClicked.connect(self.generate_story)
        self.character_widget = CharacterWidget(self)
        self.character_widget.setFont(font)
        self.character_widget.generateClicked.connect(self.generate_characters)
        self.world_widget = TextEditor(self)
        self.world_widget.setFont(font)
        self.world_widget.generateClicked.connect(self.generate_world)

        tab_widget = QtWidgets.QTabWidget(self)
        tab_widget.addTab(self.chat_widget, "Main")
        tab_widget.addTab(self.story_widget, "Story")
        tab_widget.addTab(self.character_widget, "Characters")
        tab_widget.addTab(self.world_widget, "World")
        self.setCentralWidget(tab_widget)

        # Must be at the end
        self.load_session(self.settings.session)

    def save_settings(self):
        self.settings.session = self.session.name
        g = self.geometry()
        self.settings.geometry = (g.left(), g.top(), g.width(), g.height())
        save(self.settings, SETTINGS_FILE_NAME)

    def load_session(self, name: str):
        logger.info(f"loading session {name!r}")
        names = get_session_names()
        if not name and names:
            name = names[0]
        try:
            self.session = lock_and_load(SESSION_DIRECTORY / f"{name}.json", Session)
        except IOError:
            self.session = Session()
        self.update_context_size()
        self.session_bar.set_session_manually(self.session.name)
        if self.session.save_conversation:
            memory = load(MEMORY_DIRECTORY / f"{self.session.name}.json", Memory)
        else:
            memory = Memory()
        self.chat_widget.load_messages(memory.messages)
        self.story_widget.set_text(memory.story)
        self.character_widget.characters = memory.characters
        self.world_widget.set_text(memory.world)
        self.session_bar.set_num_token(self.estimate_num_tokens())
        # self.warmup_model()

    def save_session(self):
        c = self.session
        logger.info(f"saving session {c.name!r}")
        try:
            save_and_release(c, SESSION_DIRECTORY / f"{c.name}.json")
        except ValueError:
            logger.warning("cannot save session, locked by another instance")
            return

        memory = Memory()
        memory.story = self.story_widget.text()
        memory.world = self.world_widget.text()
        memory.characters = self.character_widget.characters

        if c.save_conversation:
            widgets = self.chat_widget.messages
            memory.messages = [Message(role=w.role, content=w.content) for w in widgets]
            user_text = self.chat_widget.get_user_text()
            if user_text:
                memory.messages.append(Message(role="user", content=user_text))

        if memory == Memory():
            # remove file, if there is nothing to save
            path = MEMORY_DIRECTORY / f"{c.name}.json"
            path.unlink(missing_ok=True)
        else:
            save(memory, MEMORY_DIRECTORY / f"{c.name}.json")

    def rename_session(self, old_name: str, new_name: str):
        logger.info(f"renaming session from {old_name!r} to {new_name!r}")
        files = [
            SESSION_DIRECTORY / f"{old_name}.json",
            SESSION_DIRECTORY / f"{old_name}.lock",
            MEMORY_DIRECTORY / f"{old_name}.json",
        ]
        for f in files:
            if f.exists():
                rename(f, new_name)

    def save_all(self):
        self.save_settings()
        self.save_session()

    @QtCore.Slot()
    def configure_settings(self):
        dialog = ConfigDialog(self.settings, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.settings = dialog.result()
            # colors or font changed, we need to reload the web view
            font = self.settings.font.qfont()
            self.chat_widget.reload_style(font, self.settings.colors)
            self.story_widget.setFont(font)
            self.character_widget.setFont(font)
            self.world_widget.setFont(font)

    @QtCore.Slot()
    def configure_session(self, new_session: bool = False):
        if new_session:
            self.session = Session()
            self.chat_widget.load_messages([])
            self.story_widget.set_text("")
            self.character_widget.characters = []
            self.world_widget.set_text("")
        dialog = ConfigDialog(self.session, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            session: Session = dialog.result()
            if not new_session and self.session.name != session.name:
                self.rename_session(self.session.name, session.name)
            self.session = session
            self.session_bar.set_session_manually(self.session.name)
            self.update_context_size()
            self.session_bar.set_num_token(self.estimate_num_tokens())
            # self.warmup_model()

    @QtCore.Slot()
    def new_session(self):
        self.save_session()
        self.configure_session(new_session=True)

    @QtCore.Slot()
    def delete_session(self):
        name = self.session.name
        logger.info(f"deleting session {name}")
        for path in (
            SESSION_DIRECTORY / f"{name}.json",
            SESSION_DIRECTORY / f"{name}.lock",
            MEMORY_DIRECTORY / f"{name}.json",
        ):
            path.unlink(missing_ok=True)
        self.load_session("")

    def update_context_size(self):
        size = get_context_size(self.session.model)
        self.session_bar.set_context_size(size)

    @QtCore.Slot(str)
    def switch_session(self, name):
        if name == self.session.name:
            logger.warning(f"trying to switching same sessiion {name!r}")
            return
        logger.info(f"switching session to {name!r}")
        self.save_session()
        self.load_session(name)

    def rewind(self, partial=True):
        self.cancel_generator()
        if self.cancel_mode == "rewind":
            self.chat_widget.rewind(partial)

    def generate_response(self):
        self.chat_widget.disable()
        self.save_session()

        prompt = self.enhanced_prompt()
        # enable endless chatting by clipping the part of the conversation
        # that the LLM can see, but keep the system prompt at all times
        window = self.context_window(prompt)
        assert len(window) > 0
        self.chat_widget.messages[-(len(window) - 1)].mark()

        self.cancel_generator(wait=True)
        self.generator = Chat(
            self.session.model,
            window,
            self.settings.llm_timeout,
            temperature=self.session.temperature,
        )
        mw = self.chat_widget.add("assistant", "")
        self.generator.nextChunk.connect(mw.add_chunk)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.response_finished)
        self.cancel_mode = "rewind"
        self.generator.start()

    @QtCore.Slot()
    def response_finished(self):
        # trim excess whitespace
        messages = self.chat_widget.messages
        messages[-1].set_content(messages[-1].content.strip())

        self.chat_widget.enable()
        self.generator = None
        self.session_bar.set_num_token(self.estimate_num_tokens())

    def context_window(self, prompt: str = ""):
        window = []
        num_token = len(prompt) / CHARACTERS_PER_TOKEN
        for m in reversed(self.chat_widget.messages):
            window.append(m)
            num_token += len(m.content) / CHARACTERS_PER_TOKEN
            if num_token > self.session_bar.context_size * (
                1 - self.settings.context_margin_fraction / 100
            ):
                break
        if prompt:
            window.append(Message(role="system", content=prompt))
        window.reverse()
        return window

    def enhanced_prompt(self):
        prompt = self.session.prompt
        parts = (
            ("Characters", self.character_widget.text()),
            ("World", self.world_widget.text()),
            ("Story", self.story_widget.text()),
        )
        enhancement = "\n\n".join(
            f"# {title}\n\n{text}" for (title, text) in parts if text
        )
        return "\n\n".join((prompt, enhancement))

    def dialog_text(
        self,
        window: bool = False,
        include_world: bool = True,
        include_story: bool = True,
        include_characters: bool = True,
    ):
        world = self.world_widget.text() if include_world else ""
        story = self.story_widget.text() if include_story else ""
        characters = self.character_widget.text() if include_characters else ""
        dialog = "\n\n".join(
            f"{m.role.capitalize()}:\n{m.content}"
            for m in (self.context_window() if window else self.chat_widget.messages)
            if m.content
        )
        return "\n\n".join(x for x in (world, characters, story, dialog) if x)

    @QtCore.Slot()
    def copy_to_clipboard(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(self.dialog_text())

    @QtCore.Slot()
    def generate_story(self):
        prompt = STORY_PROMPT.format(
            dialog=self.dialog_text(window=True),
            summary=self.story_widget.text(),
        )
        logger.debug(f"generate_story\n{prompt}")

        self.cancel_generator(wait=True)
        self.cancel_mode = "cancel"
        self.generator = Generate(
            self.session.extraction_model,
            prompt=prompt,
            keep_alive=self.settings.llm_timeout,
            temperature=self.session.extraction_temperature,
        )
        self.story_widget.move_cursor_to_end()
        self.story_widget.setEnabled(False)
        self.generator.nextChunk.connect(self.story_widget.add_chunk)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generate_finished)
        self.generator.start()

    @QtCore.Slot()
    def generate_world(self):
        prompt = WORLD_PROMPT.format(dialog=self.dialog_text(window=True))

        self.cancel_generator(wait=True)
        self.cancel_mode = "cancel"
        self.generator = Generate(
            self.session.extraction_model,
            prompt=prompt,
            keep_alive=self.settings.llm_timeout,
            temperature=self.session.extraction_temperature,
        )
        self.world_widget.move_cursor_to_end()
        self.world_widget.setEnabled(False)
        self.generator.nextChunk.connect(self.world_widget.add_chunk)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generate_finished)
        self.generator.start()

    @QtCore.Slot()
    def generate_characters(self):
        prompt = CHARACTERS_PROMPT.format(dialog=self.dialog_text(window=True))

        self.cancel_generator(wait=True)
        self.cancel_mode = "cancel"
        self.generator = GenerateData(
            CharacterList,
            model=self.session.extraction_model,
            prompt=prompt,
            keep_alive=self.settings.llm_timeout,
            temperature=self.session.extraction_temperature,
        )
        self.character_widget.setEnabled(False)
        self.generator.nextChunk.connect(self.character_widget.add_chunk)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generate_characters_finished)
        self.generator.start()

    @QtCore.Slot()
    def generate_characters_finished(self):
        if self.generator.result:
            self.character_widget.integrate(self.generator.result.characters)
        self.generator = None
        self.character_widget.setEnabled(True)

    @QtCore.Slot()
    def generate_finished(self):
        self.generator = None
        self.story_widget.setEnabled(True)
        self.world_widget.setEnabled(True)

    @QtCore.Slot(str)
    def show_error_message(self, message: str):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.exec()

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

        self.generator = Generate(self.session.model, "", self.settings.llm_timeout)

        @QtCore.Slot()
        def finished():
            self.generator = None

        self.generator.finished.connect(finished)
        self.generator.start()

    def estimate_num_tokens(self):
        return estimate_num_tokens(self.chat_widget.messages, self.enhanced_prompt())


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
