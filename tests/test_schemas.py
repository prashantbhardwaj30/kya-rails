import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kya import schema

from .conftest import EX

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = sorted((ROOT / "spec" / "schemas").glob("*.schema.json"))


def kind(path: Path) -> str:
    return "manifest" if "manifest" in path.name else "action"


@pytest.mark.parametrize("path", SCHEMAS, ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(path):
    doc = json.loads(path.read_text())
    assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(doc)


@pytest.mark.parametrize("path", sorted((EX / "valid").glob("*.json")) + sorted((EX / "attacks").glob("*.json")), ids=lambda p: p.name)
def test_valid_and_attack_examples_pass_schema(path):
    assert schema.errors(kind(path), json.loads(path.read_text())) == []


EXPECTED_INVALID = {
    "raw-pan-as-principal.manifest.json": "principal_ref",
    "float-amount.manifest.json": "is not of type 'integer'",
    "unknown-field.manifest.json": "god_mode",
    "irrevocable-authority.manifest.json": "revocable",
    "unmasked-principal-name.manifest.json": "principal_display",
    "malformed-vpa.action.json": "payee/value",
    "missing-trace.action.json": "'trace' is a required property",
}


def test_every_invalid_example_is_covered():
    assert {p.name for p in (EX / "invalid").glob("*.json")} == set(EXPECTED_INVALID)


@pytest.mark.parametrize("name,needle", sorted(EXPECTED_INVALID.items()))
def test_invalid_examples_fail_for_the_named_reason(name, needle):
    path = EX / "invalid" / name
    errs = schema.errors(kind(path), json.loads(path.read_text()))
    assert errs, f"{name} should be invalid"
    assert any(needle in e for e in errs), errs


def test_examples_are_reproducible(tmp_path):
    """build_examples.py must regenerate byte-identical files (Ed25519 is deterministic)."""
    before = {p.relative_to(EX): p.read_bytes() for p in EX.rglob("*.json")}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_examples.py")], check=True, cwd=ROOT)
    after = {p.relative_to(EX): p.read_bytes() for p in EX.rglob("*.json")}
    assert before == after
