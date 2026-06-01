from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


def expand_path(value: str) -> str:
    return str(Path(os.path.expanduser(value)).resolve())


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def load_yaml(path: str) -> dict[str, Any]:
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def dump_json_atomic(path: str, data: dict[str, Any], backup: bool = True) -> None:
    target = Path(path)
    ensure_dir(str(target.parent))

    if backup and target.exists():
        bak = target.with_suffix(target.suffix + f".bak.{int(target.stat().st_mtime)}")
        shutil.copy2(target, bak)

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(target.parent)
    ) as tf:
        json.dump(data, tf, ensure_ascii=False, indent=2)
        tf.write("\n")
        tmp = tf.name
    os.replace(tmp, target)


def copy_tree(src: str, dst: str, exclude_names: set[str] | None = None) -> None:
    src_p = Path(src)
    dst_p = Path(dst)
    ensure_dir(str(dst_p))
    excluded = exclude_names or set()
    for item in src_p.iterdir():
        if item.name in excluded:
            continue
        target = dst_p / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str, content: str) -> None:
    p = Path(path)
    ensure_dir(str(p.parent))
    p.write_text(content, encoding="utf-8")


def upsert_marker_block(original: str, begin: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    block = f"{begin}\n{body}\n{end}"
    if pattern.search(original):
        return pattern.sub(block, original)
    return f"{block}\n\n{original}" if original.strip() else f"{block}\n"
