import pytest
from plaitime.io import save, load
from pydantic import BaseModel
from tempfile import TemporaryDirectory
from pathlib import Path


class Foo(BaseModel):
    key: str = "value"


@pytest.fixture
def test_dir():
    with TemporaryDirectory() as d:
        yield Path(d)


def test_save_load(test_dir):
    foo = Foo()
    save(foo, test_dir / "test.json")
    foo2 = load(test_dir / "test.json", Foo)
    assert foo == foo2


def test_save_multiple_calls(test_dir):
    foo1 = Foo(value="baz1")
    foo2 = Foo(value="baz2")
    save(foo1, test_dir / "test.json")
    save(foo2, test_dir / "test.json")
    assert load(test_dir / "test.json", Foo) == foo2
    assert load(test_dir / "test.json.1", Foo) == foo1
