"""Adapter for reading NMS .pak archives using hgpaktool.

Implements GameArchiveReader port.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

from hgpaktool.api import HGPAKFile


class HgpakAdapter:
    """GameArchiveReader implementation backed by hgpaktool."""

    def __init__(self) -> None:
        self._pak: Optional[HGPAKFile] = None

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> HgpakAdapter:
        adapter = cls()
        adapter.open(path)
        return adapter

    def open(self, path: Union[str, Path]) -> None:
        self._pak = HGPAKFile(str(path))
        self._pak.__enter__()

    def close(self) -> None:
        if self._pak is not None:
            self._pak.__exit__(None, None, None)
            self._pak = None

    def __enter__(self) -> HgpakAdapter:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def list_files(self) -> List[str]:
        if self._pak is None:
            raise RuntimeError("Archive not opened")
        return list(self._pak.filenames)

    def extract(
        self,
        paths: Optional[List[str]] = None,
        pattern: Optional[str] = None,
    ) -> Dict[str, bytes]:
        if self._pak is None:
            raise RuntimeError("Archive not opened")

        if paths is not None:
            results = {}
            known = set(self._pak.files.keys())
            for path in paths:
                if path in known:
                    for fpath, data in self._pak.extract(path):
                        results[fpath] = data
            return results

        filter_arg = pattern if pattern is not None else None
        return {fpath: data for fpath, data in self._pak.extract(filter_arg)}
