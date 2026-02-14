"""Tests for .hg file codec: LZ4 compression and key mapping."""

import json
import struct
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nmstoolkit.core.codec import (
    compress_hg,
    decompress_hg,
    load_key_map,
    map_keys,
    read_hg_file,
    unmap_keys,
    write_hg_file,
)
from tests.conftest import MINIMAL_SAVE_JSON, make_hg_bytes


# --- LZ4 Block Decompression ---


class TestDecompressHg:
    def test_decompresses_minimal_save(self, minimal_hg_bytes):
        result = decompress_hg(minimal_hg_bytes)
        parsed = json.loads(result)
        assert parsed == MINIMAL_SAVE_JSON

    def test_decompresses_multi_block(self):
        """Data larger than 512KB should span multiple blocks."""
        big_obj = {"key": "x" * 600_000}
        hg_bytes = make_hg_bytes(big_obj)
        result = decompress_hg(hg_bytes)
        parsed = json.loads(result)
        assert parsed == big_obj

    def test_rejects_bad_magic(self):
        bad = struct.pack("<IIII", 0xDEADBEEF, 0, 0, 0)
        with pytest.raises(ValueError, match="magic"):
            decompress_hg(bad)

    def test_rejects_empty_input(self):
        with pytest.raises(ValueError):
            decompress_hg(b"")

    def test_strips_trailing_null(self, minimal_hg_bytes):
        result = decompress_hg(minimal_hg_bytes)
        assert not result.endswith("\x00")

    def test_real_save_file(self, real_save_path):
        """Integration: decompress a real save file."""
        data = real_save_path.read_bytes()
        result = decompress_hg(data)
        parsed = json.loads(result)
        assert "F2P" in parsed  # Version key
        assert isinstance(parsed["F2P"], int)


class TestCompressHg:
    def test_roundtrip_minimal(self):
        json_str = json.dumps(MINIMAL_SAVE_JSON, separators=(",", ":"))
        compressed = compress_hg(json_str)
        decompressed = decompress_hg(compressed)
        assert json.loads(decompressed) == MINIMAL_SAVE_JSON

    def test_output_starts_with_magic(self):
        json_str = json.dumps(MINIMAL_SAVE_JSON, separators=(",", ":"))
        compressed = compress_hg(json_str)
        magic = struct.unpack_from("<I", compressed, 0)[0]
        assert magic == 0xFEEDA1E5

    def test_roundtrip_large_data(self):
        """Data spanning multiple blocks round-trips correctly."""
        big_obj = {"data": "A" * 700_000, "nested": {"a": 1}}
        json_str = json.dumps(big_obj, separators=(",", ":"))
        compressed = compress_hg(json_str)
        decompressed = decompress_hg(compressed)
        assert json.loads(decompressed) == big_obj


class TestRoundtripRealFile:
    def test_real_save_roundtrip(self, real_save_path):
        """Decompress → recompress → decompress yields identical JSON."""
        original_bytes = real_save_path.read_bytes()
        json_str = decompress_hg(original_bytes)

        recompressed = compress_hg(json_str)
        json_str_2 = decompress_hg(recompressed)

        assert json.loads(json_str) == json.loads(json_str_2)


# --- Key Mapping ---


class TestLoadKeyMap:
    def test_loads_save_key_map(self, key_map_path):
        key_map = load_key_map(key_map_path)
        assert isinstance(key_map, dict)
        assert key_map["F2P"] == "Version"
        assert key_map["8>q"] == "Platform"
        assert key_map["6f="] == "PlayerStateData"
        assert len(key_map) > 1000

    def test_loads_account_key_map(self, account_key_map_path):
        key_map = load_key_map(account_key_map_path)
        assert key_map["F2P"] == "Version"
        assert key_map["B89"] == "UserSettingsData"
        assert len(key_map) > 100


class TestUnmapKeys:
    def test_unmaps_flat_dict(self):
        key_map = {"F2P": "Version", "8>q": "Platform"}
        data = {"F2P": 1234, "8>q": "Win"}
        result = unmap_keys(data, key_map)
        assert result == {"Version": 1234, "Platform": "Win"}

    def test_unmaps_nested_dict(self):
        key_map = {"a1": "Outer", "b2": "Inner", "c3": "Value"}
        data = {"a1": {"b2": {"c3": 42}}}
        result = unmap_keys(data, key_map)
        assert result == {"Outer": {"Inner": {"Value": 42}}}

    def test_unmaps_list_elements(self):
        key_map = {"a1": "Name", "b2": "Items"}
        data = {"b2": [{"a1": "one"}, {"a1": "two"}]}
        result = unmap_keys(data, key_map)
        assert result == {"Items": [{"Name": "one"}, {"Name": "two"}]}

    def test_preserves_unknown_keys(self):
        key_map = {"a1": "Known"}
        data = {"a1": 1, "zz": 2}
        result = unmap_keys(data, key_map)
        assert result == {"Known": 1, "zz": 2}

    def test_preserves_scalar_values(self):
        key_map = {"a1": "Name"}
        data = {"a1": "hello"}
        result = unmap_keys(data, key_map)
        assert result["Name"] == "hello"


class TestMapKeys:
    def test_maps_flat_dict(self):
        key_map = {"F2P": "Version", "8>q": "Platform"}
        data = {"Version": 1234, "Platform": "Win"}
        result = map_keys(data, key_map)
        assert result == {"F2P": 1234, "8>q": "Win"}

    def test_maps_nested_dict(self):
        key_map = {"a1": "Outer", "b2": "Inner", "c3": "Value"}
        data = {"Outer": {"Inner": {"Value": 42}}}
        result = map_keys(data, key_map)
        assert result == {"a1": {"b2": {"c3": 42}}}

    def test_roundtrip_unmap_map(self):
        key_map = {"F2P": "Version", "8>q": "Platform", "6f=": "PlayerStateData"}
        original = {"F2P": 1234, "8>q": "Win", "6f=": {"F2P": 99}}
        unmapped = unmap_keys(original, key_map)
        remapped = map_keys(unmapped, key_map)
        assert remapped == original

    def test_preserves_unknown_keys(self):
        key_map = {"a1": "Known"}
        data = {"Known": 1, "unknown_key": 2}
        result = map_keys(data, key_map)
        assert result == {"a1": 1, "unknown_key": 2}


class TestRealKeyMappingRoundtrip:
    def test_unmap_remap_real_save(self, real_save_path, key_map_path):
        """Full roundtrip: decompress → unmap → remap → compare."""
        data = real_save_path.read_bytes()
        json_str = decompress_hg(data)
        original = json.loads(json_str)

        key_map = load_key_map(key_map_path)
        unmapped = unmap_keys(original, key_map)
        remapped = map_keys(unmapped, key_map)

        assert remapped == original

    def test_unmapped_has_readable_keys(self, real_save_path, key_map_path):
        data = real_save_path.read_bytes()
        json_str = decompress_hg(data)
        original = json.loads(json_str)

        key_map = load_key_map(key_map_path)
        unmapped = unmap_keys(original, key_map)

        assert "Version" in unmapped
        assert "Platform" in unmapped


# --- File I/O ---


class TestReadWriteHgFile:
    def test_read_hg_file(self, minimal_hg_file):
        result = read_hg_file(minimal_hg_file)
        assert result == MINIMAL_SAVE_JSON

    def test_write_and_read_back(self, tmp_path):
        path = tmp_path / "output.hg"
        write_hg_file(path, MINIMAL_SAVE_JSON)
        result = read_hg_file(path)
        assert result == MINIMAL_SAVE_JSON

    def test_read_plain_json_account(self, real_account_path):
        """accountdata.hg is plain JSON, not LZ4 compressed."""
        result = read_hg_file(real_account_path)
        assert "F2P" in result
        assert isinstance(result["F2P"], int)

    def test_read_real_save(self, real_save_path):
        result = read_hg_file(real_save_path)
        assert "F2P" in result
        assert isinstance(result["F2P"], int)

    def test_write_creates_valid_hg(self, tmp_path):
        path = tmp_path / "test.hg"
        obj = {"F2P": 9999, "data": {"nested": [1, 2, 3]}}
        write_hg_file(path, obj)

        raw = path.read_bytes()
        magic = struct.unpack_from("<I", raw, 0)[0]
        assert magic == 0xFEEDA1E5


# --- Hypothesis Property Tests ---


json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**53), max_value=2**53),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=100),
)

json_values = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
    ),
    max_leaves=20,
)


class TestHypothesisCodec:
    @given(data=st.dictionaries(st.text(min_size=1, max_size=10), json_values, max_size=5))
    @settings(max_examples=50)
    def test_compress_decompress_roundtrip(self, data):
        json_str = json.dumps(data, separators=(",", ":"))
        compressed = compress_hg(json_str)
        decompressed = decompress_hg(compressed)
        assert json.loads(decompressed) == data

    @given(
        data=st.dictionaries(
            st.text(alphabet="abcdefghijklmnop", min_size=2, max_size=3),
            json_primitives,
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=50)
    def test_key_mapping_roundtrip(self, data):
        """Arbitrary dicts survive unmap→map with an identity key_map."""
        # Build identity-ish key_map from actual keys
        key_map = {k: f"mapped_{k}" for k in data}
        unmapped = unmap_keys(data, key_map)
        remapped = map_keys(unmapped, key_map)
        assert remapped == data
