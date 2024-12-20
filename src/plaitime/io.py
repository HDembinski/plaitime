from pydantic import BaseModel
from pathlib import Path
from logging.handlers import RotatingFileHandler
import logging
from typing import TypeVar
from contextlib import closing
import os
import psutil

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def save(obj: BaseModel, filename: Path):
    data = obj.model_dump_json(indent=4)
    if filename.exists():
        with open(filename, encoding="utf-8") as f:
            if data == f.read().rstrip():
                logger.info(f"no change with respect to {filename}")
                return
    logger.info(f"saving to {filename}")
    with closing(
        RotatingFileHandler(
            filename, mode="w", encoding="utf-8", maxBytes=1, backupCount=9
        )
    ) as handler:
        record = logging.makeLogRecord({"msg": data})
        handler.emit(record)


def load(filename: Path, cls: T) -> T:
    if filename.exists():
        try:
            with open(filename, encoding="utf-8") as f:
                return cls.model_validate_json(f.read())
        except Exception as e:
            logger.error(e)
    else:
        logger.warning(f"{filename} does not exist")
    return cls()


def lock_and_load(filename: Path, cls: T) -> T:
    if filename.exists():
        lock_file = filename.with_suffix(".lock")
        if lock_file.exists():
            with lock_file.open() as f:
                pid = int(f.read())
            active_pids = [proc.pid for proc in psutil.process_iter(attrs=["pid"])]
            if pid in active_pids:
                raise IOError("file is locked")
        with lock_file.open("w") as f:
            f.write(str(os.getpid()))
    return load(filename, cls)


def save_and_release(obj: BaseModel, filename: Path):
    pid = os.getpid()
    lock_file = filename.with_suffix(".lock")
    if lock_file.exists():
        with lock_file.open() as f:
            if f.read() != str(pid):
                raise IOError("cannot save to locked file of another process")
        lock_file.unlink()
    save(obj, filename)


def rename(filename: Path, stem: str):
    new_name = filename.parent / f"{stem}{filename.suffix}"
    filename.rename(new_name)
