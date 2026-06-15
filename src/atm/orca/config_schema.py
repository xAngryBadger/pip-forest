"""Configuration schema with validation using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ConfigSchema:
    """Schema for config.json with validation in __post_init__."""

    de_para: dict[str, Any] = field(default_factory=dict)
    tarifas: dict[str, Any] = field(default_factory=dict)
    atividades: dict[str, Any] = field(default_factory=dict)
    sequencia: dict[str, Any] = field(default_factory=dict)
    comparativo: dict[str, Any] = field(default_factory=dict)
    empresas: dict[str, Any] = field(default_factory=dict)
    fazendas_ct: list[Any] = field(default_factory=list)
    filtros_bloqueio_global: list[str] = field(default_factory=list)
    orcamento_estrito: bool = True
    modo_somente_hh: bool = True
    preco_final_json_path: str = ""
    custo_hora_tf: float | None = None
    rendimento_hh_fallback: float | None = None
    rendimento_hm_fallback: float | None = None
    preco_ha_fallback: float | None = None
    custos_globais: dict[str, Any] = field(default_factory=dict)
    jornada_h: float | None = None
    executores: dict[str, Any] = field(default_factory=dict)
    meta_meses: int | None = None
    data_inicio: str | None = None
    usar_cascata_global: bool = False
    arquivo_micro: str = ""
    output_dir: str = ""
    jornada_horas: float | None = None
    coluna_metodologia_micro: str = ""

    _strict: bool = field(default=False, init=False, repr=False)

    @classmethod
    def from_dict(cls, cfg: dict[str, Any], strict: bool = False) -> "ConfigSchema":
        """Create ConfigSchema from dict with optional strict validation."""
        schema = cls()
        for key, value in cfg.items():
            if hasattr(schema, key):
                setattr(schema, key, value)
        schema._strict = strict
        schema.__post_init__()
        return schema

    def __post_init__(self) -> None:
        """Validate all fields, log warnings, and correct invalid values."""
        self.de_para = self._validate_and_correct_dict("de_para", self.de_para)
        self.tarifas = self._validate_and_correct_dict("tarifas", self.tarifas)
        self.atividades = self._validate_and_correct_dict("atividades", self.atividades)
        self.sequencia = self._validate_and_correct_dict("sequencia", self.sequencia)
        self.comparativo = self._validate_and_correct_dict("comparativo", self.comparativo)
        self.empresas = self._validate_and_correct_dict("empresas", self.empresas)
        self.custos_globais = self._validate_and_correct_dict("custos_globais", self.custos_globais)
        self.executores = self._validate_and_correct_dict("executores", self.executores)

        self.fazendas_ct = self._validate_and_correct_list("fazendas_ct", self.fazendas_ct)
        self.filtros_bloqueio_global = self._validate_and_correct_list("filtros_bloqueio_global", self.filtros_bloqueio_global, str)

        self.orcamento_estrito = self._validate_and_correct_bool("orcamento_estrito", self.orcamento_estrito, True)
        self.modo_somente_hh = self._validate_and_correct_bool("modo_somente_hh", self.modo_somente_hh, True)
        self.usar_cascata_global = self._validate_and_correct_bool("usar_cascata_global", self.usar_cascata_global, False)

        self.preco_final_json_path = self._validate_and_correct_str("preco_final_json_path", self.preco_final_json_path, "")
        self.arquivo_micro = self._validate_and_correct_str("arquivo_micro", self.arquivo_micro, "")
        self.output_dir = self._validate_and_correct_str("output_dir", self.output_dir, "")

        self.custo_hora_tf = self._validate_and_correct_optional_float("custo_hora_tf", self.custo_hora_tf)
        self.rendimento_hh_fallback = self._validate_and_correct_optional_float("rendimento_hh_fallback", self.rendimento_hh_fallback)
        self.rendimento_hm_fallback = self._validate_and_correct_optional_float("rendimento_hm_fallback", self.rendimento_hm_fallback)
        self.preco_ha_fallback = self._validate_and_correct_optional_float("preco_ha_fallback", self.preco_ha_fallback)
        self.jornada_h = self._validate_and_correct_optional_float("jornada_h", self.jornada_h)

        self.meta_meses = self._validate_and_correct_optional_int("meta_meses", self.meta_meses)

        self.data_inicio = self._validate_and_correct_optional_str("data_inicio", self.data_inicio)

        self.jornada_horas = self._validate_and_correct_optional_float("jornada_horas", self.jornada_horas)
        self.coluna_metodologia_micro = self._validate_and_correct_optional_str("coluna_metodologia_micro", self.coluna_metodologia_micro)

        if "execucao_compacta" in self.comparativo:
            self.comparativo["execucao_compacta"] = self._validate_and_correct_bool("comparativo.execucao_compacta", self.comparativo["execucao_compacta"], True)

    def _validate_and_correct_dict(self, name: str, value: Any, default: dict | None = None) -> dict[str, Any]:
        if default is None:
            default = {}
        if value is None:
            if self._strict:
                raise ValueError(f"Config key '{name}' is None, expected dict")
            logger.warning("Config key '%s' is None, expected dict. Using empty dict.", name)
            return default
        if not isinstance(value, dict):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be dict, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be dict, got %s. Using empty dict.",
                name,
                type(value).__name__,
            )
            return default
        return value

    def _validate_and_correct_list(self, name: str, value: Any, item_type: type | None = None, default: list | None = None) -> list[Any]:
        if default is None:
            default = []
        if value is None:
            if self._strict:
                raise ValueError(f"Config key '{name}' is None, expected list")
            logger.warning("Config key '%s' is None, expected list. Using empty list.", name)
            return default
        if not isinstance(value, list):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be list, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be list, got %s. Using empty list.",
                name,
                type(value).__name__,
            )
            return default
        if item_type is not None:
            corrected = []
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    if self._strict:
                        raise ValueError(f"Config key '{name}[{i}]' must be {item_type.__name__}, got {type(item).__name__}")
                    logger.warning(
                        "Config key '%s[%d]' must be %s, got %s. Skipping.",
                        name,
                        i,
                        item_type.__name__,
                        type(item).__name__,
                    )
                else:
                    corrected.append(item)
            return corrected
        return value

    def _validate_and_correct_bool(self, name: str, value: Any, default: bool) -> bool:
        if not isinstance(value, bool):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be bool, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be bool, got %s. Using default: %s.",
                name,
                type(value).__name__,
                default,
            )
            return default
        return value

    def _validate_and_correct_str(self, name: str, value: Any, default: str) -> str:
        if not isinstance(value, str):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be str, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be str, got %s. Using default: %r.",
                name,
                type(value).__name__,
                default,
            )
            return default
        return value

    def _validate_and_correct_optional_float(self, name: str, value: Any) -> float | None:
        if value is not None and not isinstance(value, (int, float)):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be numeric or None, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be numeric or None, got %s. Using None.",
                name,
                type(value).__name__,
            )
            return None
        return float(value) if value is not None else None

    def _validate_and_correct_optional_int(self, name: str, value: Any) -> int | None:
        if value is not None and not isinstance(value, int):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be int or None, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be int or None, got %s. Using None.",
                name,
                type(value).__name__,
            )
            return None
        return value

    def _validate_and_correct_optional_str(self, name: str, value: Any) -> str | None:
        if value is not None and not isinstance(value, str):
            if self._strict:
                raise ValueError(f"Config key '{name}' must be str or None, got {type(value).__name__}")
            logger.warning(
                "Config key '%s' must be str or None, got %s. Using None.",
                name,
                type(value).__name__,
            )
            return None
        return value


def validate_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Validate config dict using ConfigSchema (lenient mode).

    Creates ConfigSchema instance which triggers __post_init__ validation
    and correction. Returns the corrected config dict.
    """
    try:
        schema = ConfigSchema.from_dict(cfg, strict=False)
        return schema.__dict__
    except Exception as e:
        logger.warning("Config validation encountered an issue: %s", e)
        return cfg


def validate_config_strict(cfg: dict[str, Any]) -> dict[str, Any]:
    """Validate config dict strictly - raises on any validation error.

    Used for saving config to ensure only valid configs are persisted.
    """
    ConfigSchema.from_dict(cfg, strict=True)
    return cfg