"""Portia-owned and structurally safe identifier primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from portia.models.errors import PortiaLocalValidationError

_SAFE_EXTERNAL: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PORTIA_SUFFIX: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

PORTIA_ID_PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "evt_", "sup_", "spp_", "spn_", "spg_", "spt_", "int_", "imp_", "fid_",
        "fup_", "out_", "ren_", "rpr_", "actr_", "acp_", "asrel_", "arsc_", "ep_",
        "epr_", "acct_", "obs_", "rvw_", "cls_", "hyp_", "det_", "rsp_", "comm_",
        "rel_", "lct_", "lhc_", "amd_", "sod_", "dep_", "mig_", "owc_", "rmv_",
        "op_", "step_", "qnt_", "fack_", "fsup_", "dgen_", "pexp_",
    }
)


def validate_external_id(value: object, field_name: str = "identifier") -> str:
    """Apply Portia's nonauthoritative structurally-safe external-ID check."""
    if not isinstance(value, str):
        raise PortiaLocalValidationError(f"{field_name} must be a string.")
    if not 1 <= len(value) <= 128 or _SAFE_EXTERNAL.fullmatch(value) is None:
        raise PortiaLocalValidationError(
            f"{field_name} is not a structurally safe external identifier."
        )
    return value


def validate_portia_id(value: object, prefix: str, field_name: str = "identifier") -> str:
    """Validate one Portia-owned opaque identifier with the exact required prefix."""
    if prefix not in PORTIA_ID_PREFIXES:
        raise ValueError(f"unknown Portia identifier prefix: {prefix}")
    if not isinstance(value, str):
        raise PortiaLocalValidationError(f"{field_name} must be a string.")
    if not value.startswith(prefix):
        raise PortiaLocalValidationError(f"{field_name} must start with {prefix!r}.")
    suffix = value[len(prefix) :]
    if len(value) > 128 or _PORTIA_SUFFIX.fullmatch(suffix) is None:
        raise PortiaLocalValidationError(f"{field_name} is not a valid Portia identifier.")
    return value


@dataclass(frozen=True, slots=True)
class PortiaIdentifier:
    """An immutable Portia identifier retaining its public prefix."""

    value: str
    prefix: str

    def __post_init__(self) -> None:
        validate_portia_id(self.value, self.prefix)

    def __str__(self) -> str:
        return self.value
