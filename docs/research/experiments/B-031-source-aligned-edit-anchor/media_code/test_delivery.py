"""Small contract tests for stage reporting without inventing successful artifacts."""
from pathlib import Path

from delivery import anchor_state


def test_missing_anchor_reports_not_run(tmp_path: Path) -> None:
    # Given an untouched case, when reporting, then it remains NOT_RUN.
    assert anchor_state(tmp_path) == 'NOT_RUN'


def test_failed_attempt_is_not_success(tmp_path: Path) -> None:
    # Given a persisted attempt without an image, when reporting, then failure stays visible.
    (tmp_path / 'attempt.json').write_text('{"attempt":1}')
    assert anchor_state(tmp_path) == 'ATTEMPTED_WITHOUT_OUTPUT'


def test_image_exists_is_not_quality_pass(tmp_path: Path) -> None:
    # Given a saved image, when reporting, then its visual acceptance remains separate.
    (tmp_path / 'A0.png').write_bytes(b'test image placeholder')
    assert anchor_state(tmp_path) == 'RAW_SAVED_REVIEW_SEPARATE'
