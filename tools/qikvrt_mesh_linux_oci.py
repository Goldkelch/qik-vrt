#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build a deterministic, offline OCI/Docker prototype image.

The image contains one statically linked POSIX daemon.  Docker, a registry and
network access are deliberately not part of this builder.  ANSI C89 and ISO
C90 are compiled as two conformance invocations of one source profile; they
are not represented as independent implementations.
"""
from __future__ import annotations

import argparse
import datetime as _datetime
import gzip
import hashlib
import io
import json
import os
import pathlib
import platform
import shlex
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
from typing import Any, Iterable, Mapping, Sequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
DAEMON_SOURCE = ROOT / "platform/qikvrt-mesh-linux/qikvrt_meshd.c"
CORE_SOURCE = ROOT / "src/effect_ack_core.c"
HEADER_SOURCE = ROOT / "include/qikvrt/effect_ack.h"
LICENSE_SOURCE = ROOT / "LICENSES/PolyForm-Noncommercial-1.0.0.txt"
CAPABILITY_POLICY_SOURCE = (
    ROOT / "policy/QIKVRT_MESH_LINUX_CAPABILITY_MATRIX_V1.json"
)

SCHEMA = "qikvrt_mesh_linux_oci_receipt_v1"
VERIFICATION_SCHEMA = "qikvrt_mesh_linux_oci_verification_v1"
CAPABILITY_SCHEMA = "qikvrt_mesh_linux_capability_boundary_v1"
IMAGE_REF = "qikvrt/mesh-linux:prototype"
IMAGE_ENTRYPOINT = "/usr/bin/qikvrt-meshd"
IMAGE_PORT = "8080/tcp"
RUNTIME_UID_GID = "65532:65532"
DEFAULT_SOURCE_DATE_EPOCH = 0
MAX_COMMAND_OUTPUT = 64 * 1024
MAX_JSON_BYTES = 1 * 1024 * 1024
MAX_BINARY_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_LAYER_BYTES = 64 * 1024 * 1024
MAX_ROOTFS_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 128
OCI_MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
OCI_INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
OCI_CONFIG_MEDIA_TYPE = "application/vnd.oci.image.config.v1+json"
OCI_LAYER_MEDIA_TYPE = "application/vnd.oci.image.layer.v1.tar+gzip"
ELF_MACHINE_TO_OCI = {
    3: "386",
    40: "arm",
    62: "amd64",
    183: "arm64",
}


class BuildError(RuntimeError):
    """Raised when a fail-closed build or artifact validation step fails."""


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bytes(path: pathlib.Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def _read_regular_bounded(path: pathlib.Path, maximum: int) -> bytes:
    """Read one regular file without following a final symlink."""
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise BuildError("cannot open bounded regular file: " + str(path)) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise BuildError("path is not a regular file: " + str(path))
        if metadata.st_size < 0 or metadata.st_size > maximum:
            raise BuildError("file exceeds its byte bound: " + str(path))
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > maximum or len(data) != metadata.st_size:
            raise BuildError("file changed or exceeded its byte bound: " + str(path))
        return data
    finally:
        os.close(descriptor)


def _run(
    command: Sequence[str], environment: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            cwd=ROOT,
            env=dict(environment),
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuildError("bounded command execution failed: " + str(exc)) from exc
    if len(result.stdout.encode("utf-8", errors="replace")) > MAX_COMMAND_OUTPUT:
        raise BuildError("command stdout exceeded the receipt bound")
    if len(result.stderr.encode("utf-8", errors="replace")) > MAX_COMMAND_OUTPUT:
        raise BuildError("command stderr exceeded the receipt bound")
    if result.returncode != 0:
        rendered = " ".join(shlex.quote(part) for part in command)
        raise BuildError(
            "command failed with exit code "
            + str(result.returncode)
            + ": "
            + rendered
            + "\n"
            + result.stderr
        )
    return result


def _receipt_command(
    command: Sequence[str], build_directory: pathlib.Path
) -> list[str]:
    root = str(ROOT)
    build = str(build_directory)
    rendered: list[str] = []
    for part in command:
        rendered.append(
            part.replace(build, "${BUILD_DIR}").replace(root, "${REPO_ROOT}")
        )
    return rendered


def _source_digest(path: pathlib.Path) -> dict[str, Any]:
    data = _read_regular_bounded(path, MAX_JSON_BYTES)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": _sha256(data),
    }


def _assert_static_elf(path: pathlib.Path) -> dict[str, Any]:
    data = _read_regular_bounded(path, MAX_BINARY_BYTES)
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise BuildError("runtime artifact is not an ELF executable")
    elf_class = data[4]
    elf_data = data[5]
    if elf_class not in (1, 2) or elf_data not in (1, 2):
        raise BuildError("runtime artifact has an unsupported ELF encoding")
    endian = "<" if elf_data == 1 else ">"
    machine_code = struct.unpack_from(endian + "H", data, 18)[0]
    if machine_code not in ELF_MACHINE_TO_OCI:
        raise BuildError("runtime artifact has an unsupported ELF machine")
    if elf_class == 1:
        phoff = struct.unpack_from(endian + "I", data, 28)[0]
        phentsize = struct.unpack_from(endian + "H", data, 42)[0]
        phnum = struct.unpack_from(endian + "H", data, 44)[0]
    else:
        phoff = struct.unpack_from(endian + "Q", data, 32)[0]
        phentsize = struct.unpack_from(endian + "H", data, 54)[0]
        phnum = struct.unpack_from(endian + "H", data, 56)[0]
    if phentsize < 4 or phnum == 0 or phoff + phentsize * phnum > len(data):
        raise BuildError("runtime artifact has an invalid program-header table")
    program_types = [
        struct.unpack_from(endian + "I", data, phoff + phentsize * index)[0]
        for index in range(phnum)
    ]
    if 2 in program_types or 3 in program_types:
        raise BuildError("runtime artifact contains PT_DYNAMIC or PT_INTERP")
    return {
        "format": "ELF",
        "class_bits": 32 if elf_class == 1 else 64,
        "byte_order": "little" if elf_data == 1 else "big",
        "machine_code": machine_code,
        "oci_architecture": ELF_MACHINE_TO_OCI[machine_code],
        "program_header_count": phnum,
        "pt_dynamic": False,
        "pt_interp": False,
    }


def _build_environment(source_date_epoch: int) -> dict[str, str]:
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    environment["TZ"] = "UTC"
    environment["SOURCE_DATE_EPOCH"] = str(source_date_epoch)
    return environment


def _compile_profile(
    standard: str,
    compiler: Sequence[str],
    build_directory: pathlib.Path,
    environment: Mapping[str, str],
) -> tuple[pathlib.Path, dict[str, Any]]:
    output = build_directory / ("qikvrt-meshd-" + standard)
    common = [
        "-std=" + standard,
        "-pedantic",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-D_POSIX_C_SOURCE=200809L",
        "-I",
        str(ROOT / "include"),
        str(DAEMON_SOURCE),
        str(CORE_SOURCE),
    ]
    syntax_command = list(compiler) + common + ["-fsyntax-only"]
    syntax = _run(syntax_command, environment)
    compile_command = list(compiler) + common + ["-static", "-o", str(output)]
    compiled = _run(compile_command, environment)
    output.chmod(0o555)
    elf = _assert_static_elf(output)
    self_test_command = [str(output), "--self-test"]
    self_test = _run(self_test_command, environment)
    binary = _read_regular_bounded(output, MAX_BINARY_BYTES)
    receipt = {
        "standard_flag": "-std=" + standard,
        "source_profile": "single ANSI-C89/ISO-C90-compatible source profile",
        "syntax_check": {
            "command": _receipt_command(syntax_command, build_directory),
            "exit_code": syntax.returncode,
            "stdout": syntax.stdout,
            "stderr": syntax.stderr,
        },
        "static_compile": {
            "command": _receipt_command(compile_command, build_directory),
            "exit_code": compiled.returncode,
            "binary_bytes": len(binary),
            "binary_sha256": _sha256(binary),
            "elf": elf,
            "stdout": compiled.stdout,
            "stderr": compiled.stderr,
        },
        "self_test": {
            "command": ["${BUILD_DIR}/qikvrt-meshd-" + standard, "--self-test"],
            "exit_code": self_test.returncode,
            "stdout": self_test.stdout,
            "stderr": self_test.stderr,
        },
    }
    return output, receipt


def _tar_directory(name: str, epoch: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name.rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = epoch
    return info


def _tar_file(name: str, data: bytes, mode: int, epoch: int) -> tuple[tarfile.TarInfo, io.BytesIO]:
    info = tarfile.TarInfo(name)
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = epoch
    info.size = len(data)
    return info, io.BytesIO(data)


def _capability_boundary() -> dict[str, Any]:
    return {
        "schema": CAPABILITY_SCHEMA,
        "implemented": [
            "one strict ANSI-C89/ISO-C90 source profile compiled in both modes",
            "statically linked native Linux ELF runtime",
            "bounded POSIX HTTP reference daemon",
            "bounded EFFECT_ACK five-state evaluation",
            "offline OCI-layout and Docker-load archive construction",
        ],
        "not_implemented_or_not_observed": [
            "general Internet service suite",
            "TLS or remote peer authentication",
            "DNS or SNMP wire protocols",
            "package manager",
            "Firefox network-stack integration",
            "multi-layer OSI mediation",
            "container runtime execution",
            "registry publication or deployment",
            "independent C89 and C90 implementations",
            "general external EFFECT_ACK_DONE",
        ],
        "external_effect": "NONE_BUILD_AND_LOCAL_SELF_TEST_ONLY",
        "network_operation_requested": False,
        "registry_contacted": False,
        "publication_performed": False,
        "deployment_performed": False,
        "container_execution_observed": False,
        "distribution_authorized": False,
        "third_party_runtime_license_review_completed": False,
        "unauthenticated_http_ordinary_release": False,
        "http_core_done_is_candidate_only": True,
        "general_effect_ack_done": False,
    }


def _build_input_receipt() -> dict[str, Any]:
    capability_bytes = _canonical_json(_capability_boundary())
    return {
        "builder": _source_digest(pathlib.Path(__file__)),
        "license": _source_digest(LICENSE_SOURCE),
        "capability_policy": _source_digest(CAPABILITY_POLICY_SOURCE),
        "embedded_capability_boundary": {
            "bytes": len(capability_bytes),
            "sha256": _sha256(capability_bytes),
        },
    }


def _rootfs_tar(binary: bytes, epoch: int) -> bytes:
    if len(binary) > MAX_BINARY_BYTES:
        raise BuildError("runtime binary exceeds the image bound")
    capabilities = _canonical_json(_capability_boundary())
    files = {
        "usr/bin/qikvrt-meshd": (binary, 0o555),
        "usr/share/licenses/qik-vrt/PolyForm-Noncommercial-1.0.0.txt": (
            _read_regular_bounded(LICENSE_SOURCE, MAX_JSON_BYTES),
            0o444,
        ),
        "usr/share/qikvrt/CAPABILITY_BOUNDARY.json": (capabilities, 0o444),
    }
    directories = [
        "usr",
        "usr/bin",
        "usr/share",
        "usr/share/licenses",
        "usr/share/licenses/qik-vrt",
        "usr/share/qikvrt",
    ]
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for directory in directories:
            archive.addfile(_tar_directory(directory, epoch))
        for name in sorted(files):
            data, mode = files[name]
            info, stream = _tar_file(name, data, mode, epoch)
            archive.addfile(info, stream)
    value = output.getvalue()
    if len(value) > MAX_ROOTFS_BYTES:
        raise BuildError("root filesystem archive exceeds its byte bound")
    return value


def _gzip_layer(data: bytes, epoch: int) -> bytes:
    if len(data) > MAX_ROOTFS_BYTES:
        raise BuildError("root filesystem input exceeds its byte bound")
    output = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        fileobj=output,
        mtime=epoch,
        compresslevel=9,
    ) as stream:
        stream.write(data)
    value = output.getvalue()
    if len(value) > MAX_LAYER_BYTES:
        raise BuildError("compressed OCI layer exceeds its byte bound")
    return value


def _created(epoch: int) -> str:
    return (
        _datetime.datetime.fromtimestamp(epoch, tz=_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _image_platform() -> tuple[str, str, str | None]:
    if sys.platform != "linux":
        raise BuildError("the prototype image builder currently requires a Linux build host")
    machine = platform.machine().lower()
    mappings = {
        "x86_64": ("amd64", None),
        "amd64": ("amd64", None),
        "aarch64": ("arm64", "v8"),
        "arm64": ("arm64", "v8"),
        "i386": ("386", None),
        "i686": ("386", None),
        "armv7l": ("arm", "v7"),
    }
    if machine not in mappings:
        raise BuildError("unsupported OCI architecture: " + machine)
    architecture, variant = mappings[machine]
    return "linux", architecture, variant


def _image_config(
    epoch: int,
    architecture: str,
    os_name: str,
    variant: str | None,
    diff_id: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "architecture": architecture,
        "os": os_name,
        "created": _created(epoch),
        "config": {
            "User": RUNTIME_UID_GID,
            "Entrypoint": [IMAGE_ENTRYPOINT],
            "Cmd": ["--bind", "0.0.0.0", "--port", "8080"],
            "ExposedPorts": {IMAGE_PORT: {}},
            "Env": ["PATH=/usr/bin"],
            "Labels": {
                "org.opencontainers.image.title": "QIK-VRT Mesh Linux prototype",
                "org.opencontainers.image.version": "0.1.0-prototype",
                "org.qikvrt.external-effect": "none-build-only",
                "org.qikvrt.general-effect-ack-done": "false",
            },
        },
        "rootfs": {"type": "layers", "diff_ids": ["sha256:" + diff_id]},
        "history": [
            {
                "created": _created(epoch),
                "created_by": "qikvrt_mesh_linux_oci.py offline deterministic build",
            }
        ],
    }
    if variant is not None:
        value["variant"] = variant
    return value


def _descriptor(media_type: str, data: bytes) -> dict[str, Any]:
    return {
        "mediaType": media_type,
        "digest": "sha256:" + _sha256(data),
        "size": len(data),
    }


def _tar_mapping(files: Mapping[str, bytes], epoch: int) -> bytes:
    if len(files) > MAX_ARCHIVE_MEMBERS:
        raise BuildError("archive input exceeds its member bound")
    if sum(len(data) for data in files.values()) > MAX_ARCHIVE_BYTES:
        raise BuildError("archive input exceeds its aggregate byte bound")
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        directories: set[str] = set()
        for name in files:
            parent = pathlib.PurePosixPath(name).parent
            while parent.as_posix() not in ("", "."):
                directories.add(parent.as_posix())
                parent = parent.parent
        for directory in sorted(directories):
            archive.addfile(_tar_directory(directory, epoch))
        for name in sorted(files):
            info, stream = _tar_file(name, files[name], 0o444, epoch)
            archive.addfile(info, stream)
    value = output.getvalue()
    if len(value) > MAX_ARCHIVE_BYTES:
        raise BuildError("archive exceeds its byte bound")
    return value


def _oci_layout(
    output_directory: pathlib.Path,
    config: bytes,
    layer: bytes,
    os_name: str,
    architecture: str,
    variant: str | None,
    epoch: int,
) -> tuple[bytes, dict[str, Any]]:
    config_descriptor = _descriptor(
        OCI_CONFIG_MEDIA_TYPE, config
    )
    layer_descriptor = _descriptor(
        OCI_LAYER_MEDIA_TYPE, layer
    )
    manifest = _canonical_json(
        {
            "schemaVersion": 2,
            "mediaType": OCI_MANIFEST_MEDIA_TYPE,
            "config": config_descriptor,
            "layers": [layer_descriptor],
        }
    )
    manifest_descriptor = _descriptor(
        OCI_MANIFEST_MEDIA_TYPE, manifest
    )
    manifest_descriptor["annotations"] = {
        "org.opencontainers.image.ref.name": IMAGE_REF
    }
    platform_value: dict[str, str] = {
        "os": os_name,
        "architecture": architecture,
    }
    if variant is not None:
        platform_value["variant"] = variant
    manifest_descriptor["platform"] = platform_value
    index = _canonical_json(
        {
            "schemaVersion": 2,
            "mediaType": OCI_INDEX_MEDIA_TYPE,
            "manifests": [manifest_descriptor],
        }
    )
    layout = _canonical_json({"imageLayoutVersion": "1.0.0"})
    files = {
        "oci-layout": layout,
        "index.json": index,
        "blobs/sha256/" + _sha256(config): config,
        "blobs/sha256/" + _sha256(layer): layer,
        "blobs/sha256/" + _sha256(manifest): manifest,
    }
    layout_directory = output_directory / "qikvrt-mesh-linux-oci"
    for name in sorted(files):
        _write_bytes(layout_directory / name, files[name])
    archive = _tar_mapping(files, epoch)
    metadata = {
        "config": config_descriptor,
        "layer": layer_descriptor,
        "manifest": manifest_descriptor,
        "layout_files": {
            name: {"bytes": len(files[name]), "sha256": _sha256(files[name])}
            for name in sorted(files)
        },
    }
    return archive, metadata


def _docker_archive(config: bytes, rootfs: bytes, epoch: int) -> bytes:
    if len(config) > MAX_JSON_BYTES or len(rootfs) > MAX_ROOTFS_BYTES:
        raise BuildError("Docker archive input exceeds its byte bound")
    config_digest = _sha256(config)
    layer_id = _sha256(rootfs)
    layer_json = _canonical_json(
        {
            "id": layer_id,
            "created": _created(epoch),
            "container_config": {"Cmd": [IMAGE_ENTRYPOINT]},
        }
    )
    manifest = _canonical_json(
        [
            {
                "Config": config_digest + ".json",
                "RepoTags": [IMAGE_REF],
                "Layers": [layer_id + "/layer.tar"],
            }
        ]
    )
    repositories = _canonical_json(
        {"qikvrt/mesh-linux": {"prototype": layer_id}}
    )
    return _tar_mapping(
        {
            "manifest.json": manifest,
            "repositories": repositories,
            config_digest + ".json": config,
            layer_id + "/VERSION": b"1.0\n",
            layer_id + "/json": layer_json,
            layer_id + "/layer.tar": rootfs,
        },
        epoch,
    )


def _validate_output_directory(output_directory: pathlib.Path) -> None:
    if output_directory.exists():
        if not output_directory.is_dir():
            raise BuildError("output path exists and is not a directory")
        if any(output_directory.iterdir()):
            raise BuildError("output directory must be absent or empty")
    else:
        output_directory.mkdir(parents=True)


def build(
    output_directory: pathlib.Path,
    source_date_epoch: int = DEFAULT_SOURCE_DATE_EPOCH,
    cc: str | None = None,
) -> dict[str, Any]:
    """Build the bounded prototype and return its deterministic receipt."""
    output_directory = pathlib.Path(output_directory).resolve()
    if source_date_epoch < 0:
        raise BuildError("SOURCE_DATE_EPOCH must be a non-negative integer")
    for source in (
        DAEMON_SOURCE,
        CORE_SOURCE,
        HEADER_SOURCE,
        LICENSE_SOURCE,
        CAPABILITY_POLICY_SOURCE,
        pathlib.Path(__file__),
    ):
        if not source.is_file():
            raise BuildError("required source is absent: " + str(source))
    _validate_output_directory(output_directory)
    compiler = shlex.split(cc if cc is not None else os.environ.get("CC", "cc"))
    if not compiler:
        raise BuildError("CC must name a compiler command")
    environment = _build_environment(source_date_epoch)
    compiler_identity = _run(compiler + ["--version"], environment)
    compiler_target = _run(compiler + ["-dumpmachine"], environment)
    target_triple = compiler_target.stdout.strip()
    if not target_triple or "\n" in target_triple or "\r" in target_triple:
        raise BuildError("compiler did not report one bounded target triple")
    os_name, architecture, variant = _image_platform()

    with tempfile.TemporaryDirectory(prefix="qikvrt-mesh-linux-build-") as temporary:
        build_directory = pathlib.Path(temporary)
        c89_binary, c89_receipt = _compile_profile(
            "c89", compiler, build_directory, environment
        )
        c90_binary, c90_receipt = _compile_profile(
            "c90", compiler, build_directory, environment
        )
        runtime_binary = _read_regular_bounded(c90_binary, MAX_BINARY_BYTES)
        shutil.copyfile(c90_binary, output_directory / "qikvrt-meshd")
        (output_directory / "qikvrt-meshd").chmod(0o555)
        c89_binary_bytes = _read_regular_bounded(c89_binary, MAX_BINARY_BYTES)

    runtime_elf = _assert_static_elf(output_directory / "qikvrt-meshd")
    if runtime_elf["oci_architecture"] != architecture:
        raise BuildError("native ELF machine does not match the OCI architecture")

    rootfs = _rootfs_tar(runtime_binary, source_date_epoch)
    compressed_layer = _gzip_layer(rootfs, source_date_epoch)
    diff_id = _sha256(rootfs)
    config_object = _image_config(
        source_date_epoch, architecture, os_name, variant, diff_id
    )
    config = _canonical_json(config_object)
    oci_archive, oci_metadata = _oci_layout(
        output_directory,
        config,
        compressed_layer,
        os_name,
        architecture,
        variant,
        source_date_epoch,
    )
    docker_archive = _docker_archive(config, rootfs, source_date_epoch)
    oci_path = output_directory / "qikvrt-mesh-linux-oci.tar"
    docker_path = output_directory / "qikvrt-mesh-linux-docker.tar"
    _write_bytes(oci_path, oci_archive, 0o444)
    _write_bytes(docker_path, docker_archive, 0o444)

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "source_date_epoch": source_date_epoch,
        "image_ref": IMAGE_REF,
        "source": [
            _source_digest(DAEMON_SOURCE),
            _source_digest(CORE_SOURCE),
            _source_digest(HEADER_SOURCE),
        ],
        "build_inputs": _build_input_receipt(),
        "compiler": {
            "command": compiler,
            "identity_first_line": compiler_identity.stdout.splitlines()[0],
            "target_triple": target_triple,
        },
        "build_host": {
            "sysname": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "manifestations": {"c89": c89_receipt, "c90": c90_receipt},
        "single_source_profile": True,
        "c89_c90_binary_equal_on_this_build_host": c89_binary_bytes
        == runtime_binary,
        "runtime_image": {
            "os": os_name,
            "architecture": architecture,
            "variant": variant,
            "user": RUNTIME_UID_GID,
            "entrypoint": [IMAGE_ENTRYPOINT],
            "arguments": ["--bind", "0.0.0.0", "--port", "8080"],
            "exposed_ports": [IMAGE_PORT],
            "rootfs_diff_id": "sha256:" + diff_id,
            "oci": oci_metadata,
        },
        "artifact_digests": {
            "qikvrt-meshd": {
                "bytes": len(runtime_binary),
                "sha256": _sha256(runtime_binary),
            },
            "qikvrt-mesh-linux-oci.tar": {
                "bytes": len(oci_archive),
                "sha256": _sha256(oci_archive),
            },
            "qikvrt-mesh-linux-docker.tar": {
                "bytes": len(docker_archive),
                "sha256": _sha256(docker_archive),
            },
        },
        "capability_boundary": _capability_boundary(),
    }
    _write_bytes(
        output_directory / "qikvrt-mesh-linux-receipt.json",
        _canonical_json(receipt),
        0o444,
    )
    return receipt


def _load_json_bytes(raw: bytes, label: str) -> Any:
    if len(raw) > MAX_JSON_BYTES:
        raise BuildError("JSON artifact exceeds its byte bound: " + label)

    def reject_constant(value: str) -> None:
        raise ValueError("non-finite JSON number: " + value)

    def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, member_value in pairs:
            if key in value:
                raise ValueError("duplicate JSON member: " + key)
            value[key] = member_value
        return value

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_members,
            parse_constant=reject_constant,
        )
        canonical = _canonical_json(value)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise BuildError("invalid JSON artifact: " + label) from exc
    if raw != canonical:
        raise BuildError("JSON artifact is not canonical: " + label)
    return value


def _load_json(path: pathlib.Path) -> tuple[bytes, Any]:
    raw = _read_regular_bounded(path, MAX_JSON_BYTES)
    value = _load_json_bytes(raw, str(path))
    return raw, value


def _verify_file_digest(
    output_directory: pathlib.Path,
    name: str,
    expected: Mapping[str, Any],
    maximum: int,
) -> bytes:
    path = output_directory / name
    if not isinstance(expected, Mapping):
        raise BuildError("artifact receipt entry is malformed: " + name)
    expected_size = expected.get("bytes")
    if (
        not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size < 0
        or expected_size > maximum
    ):
        raise BuildError("artifact receipt size is outside its bound: " + name)
    data = _read_regular_bounded(path, maximum)
    if expected.get("bytes") != len(data) or expected.get("sha256") != _sha256(data):
        raise BuildError("artifact digest mismatch: " + name)
    return data


def _verify_descriptor(
    layout_directory: pathlib.Path,
    descriptor: Mapping[str, Any],
    expected_media_type: str,
    maximum: int,
) -> bytes:
    if not isinstance(descriptor, Mapping):
        raise BuildError("OCI descriptor is not an object")
    if descriptor.get("mediaType") != expected_media_type:
        raise BuildError("OCI descriptor media type mismatch")
    digest_value = descriptor.get("digest")
    if not isinstance(digest_value, str) or not digest_value.startswith("sha256:"):
        raise BuildError("OCI descriptor has no supported SHA-256 digest")
    digest = digest_value[7:]
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise BuildError("OCI descriptor digest is malformed")
    blob = layout_directory / "blobs" / "sha256" / digest
    descriptor_size = descriptor.get("size")
    if (
        not isinstance(descriptor_size, int)
        or isinstance(descriptor_size, bool)
        or descriptor_size < 0
        or descriptor_size > maximum
    ):
        raise BuildError("OCI descriptor size is outside its bound")
    data = _read_regular_bounded(blob, maximum)
    if descriptor.get("size") != len(data) or _sha256(data) != digest:
        raise BuildError("OCI descriptor does not match its blob")
    return data


def _layout_files(layout_directory: pathlib.Path) -> dict[str, bytes]:
    if layout_directory.is_symlink() or not layout_directory.is_dir():
        raise BuildError("OCI layout directory is absent or unsafe")
    files: dict[str, bytes] = {}
    aggregate = 0
    paths: list[pathlib.Path] = []
    stack = [layout_directory]
    entries_seen = 0
    while stack:
        directory = stack.pop()
        try:
            entries = os.scandir(directory)
        except OSError as exc:
            raise BuildError("cannot enumerate OCI layout safely") from exc
        with entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > MAX_ARCHIVE_MEMBERS:
                    raise BuildError("OCI layout exceeds its entry bound")
                if entry.is_symlink():
                    raise BuildError("OCI layout contains a symbolic link")
                entry_path = pathlib.Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry_path)
                elif entry.is_file(follow_symlinks=False):
                    paths.append(entry_path)
                else:
                    raise BuildError("OCI layout contains a non-regular entry")
    for path in sorted(paths):
        relative = path.relative_to(layout_directory).as_posix()
        if len(files) >= MAX_ARCHIVE_MEMBERS:
            raise BuildError("OCI layout exceeds its member bound")
        maximum = MAX_LAYER_BYTES if relative.startswith("blobs/") else MAX_JSON_BYTES
        data = _read_regular_bounded(path, maximum)
        aggregate += len(data)
        if aggregate > MAX_ARCHIVE_BYTES:
            raise BuildError("OCI layout exceeds its aggregate byte bound")
        files[relative] = data
    return files


def _tar_files(data: bytes) -> dict[str, bytes]:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise BuildError("archive exceeds its input byte bound")
    files: dict[str, bytes] = {}
    aggregate = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            member_count = 0
            for member in archive:
                member_count += 1
                if member_count > MAX_ARCHIVE_MEMBERS:
                    raise BuildError("archive exceeds its member bound")
                path = pathlib.PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise BuildError("archive contains an unsafe path")
                if member.isdir():
                    continue
                if not member.isfile() or member.name in files:
                    raise BuildError("archive contains an unsafe or duplicate member")
                if member.size < 0 or member.size > MAX_ARCHIVE_BYTES:
                    raise BuildError("archive member exceeds its byte bound")
                aggregate += member.size
                if aggregate > MAX_ARCHIVE_BYTES:
                    raise BuildError("archive exceeds its aggregate byte bound")
                stream = archive.extractfile(member)
                if stream is None:
                    raise BuildError("archive regular member cannot be read")
                value = stream.read(member.size + 1)
                if len(value) != member.size:
                    raise BuildError("archive member size does not match its header")
                files[member.name] = value
    except tarfile.TarError as exc:
        raise BuildError("invalid tar archive") from exc
    return files


def _gzip_decompress_bounded(data: bytes) -> bytes:
    if len(data) > MAX_LAYER_BYTES:
        raise BuildError("compressed layer exceeds its input byte bound")
    output = io.BytesIO()
    total = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as stream:
            while True:
                chunk = stream.read(min(1024 * 1024, MAX_ROOTFS_BYTES - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ROOTFS_BYTES:
                    raise BuildError("expanded root filesystem exceeds its byte bound")
                output.write(chunk)
    except (OSError, EOFError) as exc:
        raise BuildError("OCI layer is not a valid bounded gzip stream") from exc
    return output.getvalue()


def verify(output_directory: pathlib.Path) -> dict[str, Any]:
    """Structurally reobserve artifacts without executing untrusted bytes."""
    output_directory = pathlib.Path(output_directory).resolve()
    receipt_path = output_directory / "qikvrt-mesh-linux-receipt.json"
    receipt_raw, receipt_value = _load_json(receipt_path)
    if not isinstance(receipt_value, dict) or receipt_value.get("schema") != SCHEMA:
        raise BuildError("unexpected build-receipt schema")
    receipt: dict[str, Any] = receipt_value
    if receipt.get("image_ref") != IMAGE_REF:
        raise BuildError("build receipt image reference mismatch")
    if receipt.get("capability_boundary") != _capability_boundary():
        raise BuildError("build receipt capability boundary mismatch")
    if receipt.get("build_inputs") != _build_input_receipt():
        raise BuildError("build receipt input digest mismatch")
    artifact_digests = receipt.get("artifact_digests")
    expected_artifacts = {
        "qikvrt-meshd",
        "qikvrt-mesh-linux-oci.tar",
        "qikvrt-mesh-linux-docker.tar",
    }
    if not isinstance(artifact_digests, dict) or set(artifact_digests) != expected_artifacts:
        raise BuildError("build receipt has an unexpected artifact digest map")
    try:
        binary = _verify_file_digest(
            output_directory,
            "qikvrt-meshd",
            artifact_digests["qikvrt-meshd"],
            MAX_BINARY_BYTES,
        )
        oci_archive = _verify_file_digest(
            output_directory,
            "qikvrt-mesh-linux-oci.tar",
            artifact_digests["qikvrt-mesh-linux-oci.tar"],
            MAX_ARCHIVE_BYTES,
        )
        docker_archive = _verify_file_digest(
            output_directory,
            "qikvrt-mesh-linux-docker.tar",
            artifact_digests["qikvrt-mesh-linux-docker.tar"],
            MAX_ARCHIVE_BYTES,
        )
    except (KeyError, TypeError) as exc:
        raise BuildError("build receipt artifact digest is malformed") from exc
    elf = _assert_static_elf(output_directory / "qikvrt-meshd")
    epoch = receipt.get("source_date_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise BuildError("build receipt has an invalid SOURCE_DATE_EPOCH")

    layout_directory = output_directory / "qikvrt-mesh-linux-oci"
    files = _layout_files(layout_directory)
    if oci_archive != _tar_mapping(files, epoch):
        raise BuildError("OCI archive is not the deterministic layout archive")
    if _tar_files(oci_archive) != files:
        raise BuildError("OCI archive members differ from the OCI layout")
    _, layout_value = _load_json(layout_directory / "oci-layout")
    if layout_value != {"imageLayoutVersion": "1.0.0"}:
        raise BuildError("unexpected OCI image-layout version")
    _, index_value = _load_json(layout_directory / "index.json")
    try:
        descriptors = index_value["manifests"]
        if (
            index_value["schemaVersion"] != 2
            or index_value.get("mediaType") != OCI_INDEX_MEDIA_TYPE
            or not isinstance(descriptors, list)
            or len(descriptors) != 1
        ):
            raise BuildError("OCI index must contain exactly one typed manifest")
        manifest_descriptor = descriptors[0]
        if manifest_descriptor.get("annotations") != {
            "org.opencontainers.image.ref.name": IMAGE_REF
        }:
            raise BuildError("OCI index reference annotation mismatch")
        manifest_bytes = _verify_descriptor(
            layout_directory,
            manifest_descriptor,
            OCI_MANIFEST_MEDIA_TYPE,
            MAX_JSON_BYTES,
        )
        manifest = _load_json_bytes(manifest_bytes, "OCI manifest blob")
        layers = manifest["layers"]
        if (
            manifest["schemaVersion"] != 2
            or manifest.get("mediaType") != OCI_MANIFEST_MEDIA_TYPE
            or not isinstance(layers, list)
            or len(layers) != 1
        ):
            raise BuildError("OCI manifest must contain exactly one typed layer")
        config_bytes = _verify_descriptor(
            layout_directory,
            manifest["config"],
            OCI_CONFIG_MEDIA_TYPE,
            MAX_JSON_BYTES,
        )
        layer_bytes = _verify_descriptor(
            layout_directory,
            layers[0],
            OCI_LAYER_MEDIA_TYPE,
            MAX_LAYER_BYTES,
        )
        config = _load_json_bytes(config_bytes, "OCI config blob")
    except (KeyError, TypeError) as exc:
        raise BuildError("OCI graph is malformed") from exc

    config_os = config.get("os")
    config_architecture = config.get("architecture")
    config_variant = config.get("variant")
    expected_platform = {
        "os": config_os,
        "architecture": config_architecture,
    }
    if config_variant is not None:
        expected_platform["variant"] = config_variant
    if (
        config_os != "linux"
        or config_architecture not in set(ELF_MACHINE_TO_OCI.values())
        or manifest_descriptor.get("platform") != expected_platform
    ):
        raise BuildError("OCI index platform does not match its image config")
    if elf["oci_architecture"] != config_architecture:
        raise BuildError("ELF machine does not match the OCI architecture")
    runtime_image = receipt.get("runtime_image")
    if not isinstance(runtime_image, dict):
        raise BuildError("build receipt runtime-image section is malformed")
    if (
        runtime_image.get("os") != config_os
        or runtime_image.get("architecture") != config_architecture
        or runtime_image.get("variant") != config_variant
    ):
        raise BuildError("build receipt platform differs from OCI config")
    if config.get("config", {}).get("User") != RUNTIME_UID_GID:
        raise BuildError("OCI runtime user is not the unprivileged identity")
    if config.get("config", {}).get("Entrypoint") != [IMAGE_ENTRYPOINT]:
        raise BuildError("OCI entrypoint mismatch")
    if config.get("config", {}).get("Cmd") != [
        "--bind",
        "0.0.0.0",
        "--port",
        "8080",
    ]:
        raise BuildError("OCI command mismatch")
    if config.get("config", {}).get("ExposedPorts") != {IMAGE_PORT: {}}:
        raise BuildError("OCI exposed-port contract mismatch")
    rootfs = _gzip_decompress_bounded(layer_bytes)
    expected_diff_ids = ["sha256:" + _sha256(rootfs)]
    if config.get("rootfs", {}).get("diff_ids") != expected_diff_ids:
        raise BuildError("OCI rootfs diff-id mismatch")
    if runtime_image.get("rootfs_diff_id") != expected_diff_ids[0]:
        raise BuildError("build receipt rootfs diff-id mismatch")
    if config != _image_config(
        epoch,
        config_architecture,
        config_os,
        config_variant,
        _sha256(rootfs),
    ):
        raise BuildError("OCI config differs from the closed runtime profile")
    if layer_bytes != _gzip_layer(rootfs, epoch):
        raise BuildError("OCI layer differs from the deterministic gzip encoding")
    rootfs_files = _tar_files(rootfs)
    if rootfs != _rootfs_tar(binary, epoch):
        raise BuildError("OCI rootfs differs from the closed deterministic profile")
    if rootfs_files.get("usr/bin/qikvrt-meshd") != binary:
        raise BuildError("OCI rootfs daemon differs from the native artifact")
    if rootfs_files.get("usr/share/qikvrt/CAPABILITY_BOUNDARY.json") != _canonical_json(
        _capability_boundary()
    ):
        raise BuildError("OCI rootfs capability boundary mismatch")
    if rootfs_files.get(
        "usr/share/licenses/qik-vrt/PolyForm-Noncommercial-1.0.0.txt"
    ) != _read_regular_bounded(LICENSE_SOURCE, MAX_JSON_BYTES):
        raise BuildError("OCI rootfs license input mismatch")
    actual_oci_metadata = {
        "config": manifest["config"],
        "layer": layers[0],
        "manifest": manifest_descriptor,
        "layout_files": {
            name: {"bytes": len(files[name]), "sha256": _sha256(files[name])}
            for name in sorted(files)
        },
    }
    if runtime_image.get("oci") != actual_oci_metadata:
        raise BuildError("build receipt OCI metadata mismatch")

    if docker_archive != _docker_archive(config_bytes, rootfs, epoch):
        raise BuildError("Docker archive is not the deterministic image archive")
    docker_files = _tar_files(docker_archive)
    try:
        docker_manifest = _load_json_bytes(
            docker_files["manifest.json"], "Docker manifest"
        )
        if not isinstance(docker_manifest, list) or len(docker_manifest) != 1:
            raise BuildError("Docker-load archive must contain exactly one image")
        config_name = docker_manifest[0]["Config"]
        layer_names = docker_manifest[0]["Layers"]
        if layer_names != [_sha256(rootfs) + "/layer.tar"]:
            raise BuildError("Docker-load archive must contain exactly one bound layer")
        layer_name = layer_names[0]
    except (KeyError, IndexError, TypeError) as exc:
        raise BuildError("Docker-load manifest is malformed") from exc
    if docker_manifest[0].get("RepoTags") != [IMAGE_REF]:
        raise BuildError("Docker-load image reference mismatch")
    if config_name != _sha256(config_bytes) + ".json":
        raise BuildError("Docker-load config name does not bind its digest")
    if docker_files.get(config_name) != config_bytes or docker_files.get(layer_name) != rootfs:
        raise BuildError("Docker-load archive content does not bind the OCI content")

    return {
        "schema": VERIFICATION_SCHEMA,
        "verified": True,
        "build_receipt_sha256": _sha256(receipt_raw),
        "artifact_digests": artifact_digests,
        "native_self_test": "NOT_EXECUTED_UNTRUSTED_BOUNDARY",
        "external_effect": "STRUCTURAL_REOBSERVATION_ONLY",
        "network_operation_requested": False,
        "registry_contacted": False,
        "publication_performed": False,
        "deployment_performed": False,
        "general_effect_ack_done": False,
    }


def _epoch_argument(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic offline QIK-VRT OCI/Docker prototype"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="build a new artifact set")
    build_parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    build_parser.add_argument(
        "--source-date-epoch",
        type=_epoch_argument,
        default=_epoch_argument(
            os.environ.get("SOURCE_DATE_EPOCH", str(DEFAULT_SOURCE_DATE_EPOCH))
        ),
    )
    build_parser.add_argument("--cc", default=None)
    verify_parser = commands.add_parser(
        "verify", help="reobserve an existing artifact set"
    )
    verify_parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if arguments.command == "build":
            result = build(
                arguments.output_dir, arguments.source_date_epoch, arguments.cc
            )
        else:
            result = verify(arguments.output_dir)
    except BuildError as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(_canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
