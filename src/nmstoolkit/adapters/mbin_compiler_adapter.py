"""Adapter for MBIN→EXML conversion using MBINCompiler.

Implements MbinConverter port by shelling out to MBINCompiler binary.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Union


def _build_command(compiler: Path, args: List[str]) -> List[str]:
    """Build command list, prepending 'wine' for .exe on non-Windows."""
    exe = str(compiler)
    if compiler.suffix.lower() == ".exe" and sys.platform != "win32":
        return ["wine", exe] + args
    return [exe] + args


class MbinCompilerAdapter:
    """MbinConverter implementation using MBINCompiler binary."""

    def __init__(self, compiler_path: Union[str, Path]) -> None:
        self._compiler = Path(compiler_path)
        if not self._compiler.exists():
            raise FileNotFoundError(f"MBINCompiler not found: {self._compiler}")

    def convert(self, mbin_data: bytes) -> str:
        """Convert MBIN bytes to EXML string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mbin_path = Path(tmpdir) / "input.mbin"
            mbin_path.write_bytes(mbin_data)

            result = subprocess.run(
                _build_command(self._compiler, [str(mbin_path)]),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"MBINCompiler failed: {result.stderr or result.stdout}"
                )

            # MBINCompiler outputs .MXML file alongside the .mbin
            mxml_path = mbin_path.with_suffix(".MXML")
            if not mxml_path.exists():
                raise RuntimeError(
                    f"MBINCompiler did not produce output file: {mxml_path}"
                )
            return mxml_path.read_text(encoding="utf-8")

    def convert_batch(self, mbin_files: Dict[str, bytes]) -> Dict[str, str]:
        """Convert multiple MBIN files to EXML strings."""
        results = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            mbin_paths = []

            for filename, data in mbin_files.items():
                safe_name = filename.replace("/", "_")
                mbin_path = tmpdir_path / safe_name
                mbin_path.write_bytes(data)
                mbin_paths.append((filename, mbin_path))

            # Convert all at once
            for original_name, mbin_path in mbin_paths:
                result = subprocess.run(
                    _build_command(self._compiler, [str(mbin_path)]),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )
                mxml_path = mbin_path.with_suffix(".MXML")
                if result.returncode == 0 and mxml_path.exists():
                    results[original_name] = mxml_path.read_text(encoding="utf-8")

        return results
