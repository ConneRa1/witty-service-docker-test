from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from witty_agent_server.application.materialization.core.io_utils import (
    load_yaml,
)


SCHEMA_VERSION = "openclaw-spec-json/v1"


def _ensure_minimal_spec(spec: dict[str, Any]) -> None:
    runtime = spec.get("runtimeType", "openclaw")
    if runtime != "openclaw":
        raise ValueError(f"runtimeType 必须是 openclaw，当前为: {runtime}")

    models = spec.get("model") or []
    if not isinstance(models, list) or not models:
        raise ValueError("agent-spec.yaml 缺少 model 配置")


def parse_agent_spec_to_json(spec_path: str) -> str:
    spec_abs = str(Path(spec_path).resolve())
    spec = load_yaml(spec_abs)
    if not isinstance(spec, dict):
        raise ValueError("agent-spec.yaml 顶层必须是对象")

    _ensure_minimal_spec(spec)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "spec_path": spec_abs,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        "spec": spec,
    }
    return json.dumps(payload, ensure_ascii=False)
