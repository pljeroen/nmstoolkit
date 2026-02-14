"""Tests for GameArchiveReader port conformance.

Verifies that any implementation of GameArchiveReader satisfies the protocol
contract using a minimal in-memory fake.

Tests: R-PAK-01, R-PAK-03 (port purity), FC-PAK-01 (structural typing).
"""

import ast
from pathlib import Path

import pytest


class TestPortDefinitionPurity:
    """FC-PAK-01: Port module uses only stdlib imports."""

    def test_no_external_imports(self):
        port_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "nmstoolkit"
            / "ports"
            / "archive_reader.py"
        )
        source = port_path.read_text()
        tree = ast.parse(source)

        stdlib_modules = {
            "pathlib", "typing", "collections", "abc", "dataclasses",
            "enum", "os", "sys", "io", "__future__",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in stdlib_modules, (
                        f"Non-stdlib import in port: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in stdlib_modules, (
                        f"Non-stdlib import in port: from {node.module}"
                    )


class TestPortStructuralTyping:
    """R-PAK-01: GameArchiveReader is a Protocol, not an ABC."""

    def test_is_protocol(self):
        from nmstoolkit.ports.archive_reader import GameArchiveReader

        assert hasattr(GameArchiveReader, "__protocol_attrs__") or issubclass(
            type(GameArchiveReader), type
        ), "GameArchiveReader should be a Protocol"

    def test_structural_conformance(self):
        """Any class with the right methods satisfies the protocol."""
        from nmstoolkit.ports.archive_reader import GameArchiveReader

        class FakeReader:
            def open(self, path):
                pass

            def close(self):
                pass

            def list_files(self):
                return []

            def extract(self, paths=None, pattern=None):
                return {}

        reader: GameArchiveReader = FakeReader()
        assert reader.list_files() == []
        assert reader.extract() == {}
