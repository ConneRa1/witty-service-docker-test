from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from witty_agent_server.application.materialization.converter import (
    ConvertOptions,
    convert_openclaw,
)
from witty_agent_server.application.materialization.ports import (
    MaterializeReport,
    SpecMaterializerPort,
)


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" / "openclaw-template.json"
)
_DEFAULT_OUTPUT_PATH = Path.home() / ".openclaw" / "openclaw.json"


class OpenClawMaterializationError(RuntimeError):
    def __init__(self, message: str, *, spec_path: Path) -> None:
        super().__init__(message)
        self.spec_path = spec_path


class SpecNotFoundError(OpenClawMaterializationError):
    pass


class InvalidOpenClawSpecError(OpenClawMaterializationError):
    pass


@dataclass(slots=True)
class OpenClawSpecMaterializer(SpecMaterializerPort):
    template_path: Path = _TEMPLATE_PATH
    output_path: Path = _DEFAULT_OUTPUT_PATH
    apply_external: bool = True
    verify_recognition: bool = True

    def materialize(self, spec_path: Path) -> MaterializeReport:
        resolved_path = spec_path.resolve()
        if not resolved_path.is_file():
            raise SpecNotFoundError(
                f"OpenClaw spec file not found: {resolved_path}",
                spec_path=resolved_path,
            )

        try:
            return self._convert_spec(resolved_path)
        except ValueError as exc:
            raise InvalidOpenClawSpecError(
                f"Invalid OpenClaw spec: {exc}",
                spec_path=resolved_path,
            ) from exc
        except Exception as exc:
            raise OpenClawMaterializationError(
                f"{exc}",
                spec_path=resolved_path,
            ) from exc

    def _convert_spec(self, spec_path: Path) -> MaterializeReport:
        report = convert_openclaw(
            ConvertOptions(
                spec_path=str(spec_path),
                template_path=str(self.template_path),
                output_path=str(self.output_path),
                apply_external=self.apply_external,
                verify_recognition=self.verify_recognition,
            )
        )
        return MaterializeReport(
            created=list(report.created),
            updated=list(report.updated),
            skipped=list(report.skipped),
            commands=list(report.commands),
        )


_DEFAULT_MATERIALIZER = OpenClawSpecMaterializer()


def materialize(spec_path: Path) -> MaterializeReport:
    return _DEFAULT_MATERIALIZER.materialize(spec_path)


__all__ = [
    "InvalidOpenClawSpecError",
    "MaterializeReport",
    "OpenClawMaterializationError",
    "OpenClawSpecMaterializer",
    "SpecNotFoundError",
    "materialize",
]
