"""Strict JSON Schema (draft 2020-12) validation for KYA manifests and action envelopes."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "spec" / "schemas"
BASE = "https://github.com/prashantbhardwaj30/kya-rails/blob/main/spec/schemas/"


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resources.append((contents["$id"], Resource.from_contents(contents)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    """name is e.g. 'manifest' or 'action'."""
    schema = _registry().get_or_retrieve(BASE + f"{name}.schema.json").value.contents
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def errors(name: str, instance: Any) -> list[str]:
    """Human-readable validation errors, sorted by path; empty list means valid."""
    out = []
    for err in validator(name).iter_errors(instance):
        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
        out.append(f"{path}: {err.message}")
    return sorted(out)
