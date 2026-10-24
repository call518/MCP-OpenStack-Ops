"""Check that tag publication rejects incorrect or incomplete distributions."""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_release import check_release


def write_distributions(directory: Path, version: str, name: str = "mcp-openstack-ops") -> None:
    metadata = f"Name: {name}\nVersion: {version}\n".encode()
    with zipfile.ZipFile(directory / "package.whl", "w") as archive:
        archive.writestr("mcp-openstack-ops.dist-info/METADATA", metadata)
    with tarfile.open(directory / "package.tar.gz", "w:gz") as archive:
        member = tarfile.TarInfo("mcp-openstack-ops/PKG-INFO")
        member.size = len(metadata)
        archive.addfile(member, io.BytesIO(metadata))


@pytest.mark.parametrize("tag", ["0.5.7", "v0.5.7", "0.5.7rc1", "v0.5.7a1"])
def test_matching_release(tag: str, tmp_path: Path) -> None:
    write_distributions(tmp_path, tag.removeprefix("v"))
    check_release(tag, tmp_path)


@pytest.mark.parametrize("tag", ["latest", "0.5", "0.5.7+dirty", "01.5.7", "0.5.7-rc1"])
def test_invalid_release_tag(tag: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Use a tag"):
        check_release(tag, tmp_path)


@pytest.mark.parametrize("version,name", [("0.5.8", "mcp-openstack-ops"), ("0.5.7", "other")])
def test_wrong_distribution(version: str, name: str, tmp_path: Path) -> None:
    write_distributions(tmp_path, version, name)
    with pytest.raises(ValueError, match="expected mcp-openstack-ops 0.5.7"):
        check_release("0.5.7", tmp_path)


def test_sdist_version_must_also_match(tmp_path: Path) -> None:
    write_distributions(tmp_path, "0.5.8")
    with zipfile.ZipFile(tmp_path / "package.whl", "w") as archive:
        archive.writestr(
            "mcp-openstack-ops.dist-info/METADATA", "Name: mcp-openstack-ops\nVersion: 0.5.7\n"
        )
    with pytest.raises(ValueError, match="package.tar.gz"):
        check_release("0.5.7", tmp_path)


def test_incomplete_distributions(tmp_path: Path) -> None:
    write_distributions(tmp_path, "0.5.7")
    (tmp_path / "package.tar.gz").unlink()
    with pytest.raises(ValueError, match="exactly one"):
        check_release("0.5.7", tmp_path)

