# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "pydantic>=2", "pillow"]
# ///
"""Contract tests use metadata only; no model or GPU is loaded."""
# Run: B031_PY -m pytest test_qwen_contract.py
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from qwen_contract import ImageContract

CONTRACT = Path(__file__).parents[1]/'INPUT_CONTRACT.json'

def test_fixed_contract_and_six_case_order() -> None:
    contract = ImageContract.model_validate_json(CONTRACT.read_text())
    contract.check_order()
    assert contract.image_steps == 40 and contract.image_attempt_limit == 6

def test_changed_output_size_is_rejected() -> None:
    data = json.loads(CONTRACT.read_text())
    data['output_request_wh'] = [512,512]
    with pytest.raises(ValidationError):
        ImageContract.model_validate(data)

def test_changed_seed_is_rejected() -> None:
    data = json.loads(CONTRACT.read_text())
    data['image_seed'] = 0
    with pytest.raises(ValidationError):
        ImageContract.model_validate(data)

def test_reordered_cases_are_rejected() -> None:
    data = json.loads(CONTRACT.read_text())
    data['cases'].reverse()
    contract = ImageContract.model_validate(data)
    with pytest.raises(AssertionError):
        contract.check_order()
