"""Inspect configuration using fake paths; never read a real .env file."""
import ast
from pathlib import Path
import runpy
import sys
from unittest.mock import Mock

import dotenv
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_examples_document_every_environment_key_used_by_settings():
    tree = ast.parse((ROOT / "Config/settings.py").read_text())
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "getenv" and node.args and isinstance(node.args[0], ast.Constant):
                keys.add(node.args[0].value)
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "environ" and isinstance(node.slice, ast.Constant):
                keys.add(node.slice.value)
    for filename in (".env.example", "Config/.env.example"):
        assert keys <= dotenv.dotenv_values(ROOT / filename).keys()


@pytest.mark.parametrize("available, expected", [((0, 1, 2), 0), ((1, 2), 1), ((2,), 2), ((), None)])
def test_env_precedence_uses_only_first_existing_path(monkeypatch, available, expected):
    paths = (Path("/virtual/bin/.env"), Path("/virtual/home/.config/bazadomowa/.env"),
             ROOT / "Config/.env")
    loader = Mock()
    monkeypatch.setattr(dotenv, "load_dotenv", loader)
    monkeypatch.setattr(sys, "executable", "/virtual/bin/python")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/virtual/home")))
    monkeypatch.setattr(Path, "exists", lambda path: path in {paths[i] for i in available})
    runpy.run_path(str(ROOT / "Config/settings.py"))
    if expected is None:
        loader.assert_not_called()
    else:
        loader.assert_called_once_with(dotenv_path=paths[expected])
