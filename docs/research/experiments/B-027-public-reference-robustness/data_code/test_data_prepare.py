"""CPU contracts for mask-given DAVIS preprocessing; no model execution."""
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from data_prepare import Selection, fit_pair, reference_pair, encode_verify


def test_reference_preserves_support_and_neutralizes_background() -> None:
    # Given: a portrait RGB image and an indexed instance support.
    rgb = Image.fromarray(np.full((12, 8, 3), [32, 64, 96], dtype=np.uint8))
    support = Image.fromarray(np.pad(np.ones((8, 4), dtype=np.uint8) * 255, 2))
    # When: reference background isolation follows the common spatial transform.
    fitted, mask, _ = fit_pair(rgb, support)
    reference, semantic = reference_pair(fitted, mask)
    selected = np.asarray(mask) != 0
    # Then: no selected RGB changes, and semantic colors follow the exact support.
    assert np.array_equal(np.asarray(reference)[selected], np.asarray(fitted)[selected])
    assert np.all(np.asarray(reference)[~selected] == 128)
    assert np.all(np.asarray(fitted)[:, :10] == 0)
    assert np.all(np.asarray(semantic)[selected] == [255, 0, 0])
    assert np.all(np.asarray(semantic)[~selected] == 0)


def test_nonconsecutive_source_is_rejected() -> None:
    # Given: an otherwise valid selection with a skipped source frame.
    task = dict(task_id='example', prompt='Example', source_sequence='source', source_track=1,
                source_frames=list(range(16)) + [18], target_sequence='target',
                target_track=1, reference_frames=[0, 20])
    # When / Then: boundary parsing refuses the altered temporal contract.
    with pytest.raises(ValueError, match='consecutive'):
        Selection.model_validate({'tasks': [task]})


def test_lossless_video_roundtrip(tmp_path: Path) -> None:
    # Given: 17 distinct RGB frames, including hard semantic colors.
    frames = [Image.fromarray(np.full((16, 24, 3), [i, 0, 255-i], dtype=np.uint8)) for i in range(17)]
    # When: the actual ffmpeg encoder and decoder are used.
    result = encode_verify(frames, tmp_path / 'video.mp4')
    # Then: all decoded bytes match all original frame bytes.
    assert result['roundtrip_rgb_exact'] is True
    assert result['frame_count'] == 17


def test_complete_task_has_real_files_and_preserved_palette(tmp_path: Path) -> None:
    # Given: a small local fixture with indexed masks for distinct source/target tracks.
    import json
    from data_prepare import Task, prepare_task
    dataset = tmp_path / 'DAVIS'
    for sequence, indices in [('source', range(17)), ('target', [0, 20])]:
        for frame in indices:
            rgb_path = dataset / 'JPEGImages/480p' / sequence / f'{frame:05d}.jpg'
            mask_path = dataset / 'Annotations/480p' / sequence / f'{frame:05d}.png'
            rgb_path.parent.mkdir(parents=True, exist_ok=True)
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', (32, 18), (frame+10, 50, 90)).save(rgb_path)
            labels = np.zeros((18, 32), dtype=np.uint8)
            labels[4:14, 8:24] = 1
            Image.fromarray(labels).convert('P').save(mask_path)
    task = Task(task_id='fixture', prompt='An object moves.', source_sequence='source', source_track=1,
                source_frames=tuple(range(17)), target_sequence='target', target_track=1, reference_frames=(0, 20))
    # When: the actual full preparer runs once, with both encodes and decodes.
    prepare_task(dataset, task, tmp_path/'out', 'fixed-selection-fixture')
    # Then: manifest, complete media, input preservation, and exact references are present.
    root = tmp_path/'out/tasks/fixture'
    manifest = json.loads((root/'task_manifest.json').read_text())
    assert manifest['source_fps'] is None and manifest['timebase_assumed'] is True
    assert len(list((root/'inputs/source').glob('*.png'))) == 17
    assert manifest['videos']['driver']['roundtrip_rgb_exact'] is True
    assert manifest['videos']['driver_mask']['roundtrip_rgb_exact'] is True
    assert (root/'inputs/R1/original/instance-mask.png').read_bytes() == (dataset/'Annotations/480p/target/00000.png').read_bytes()
    assert all(reference['subject_rgb_exact'] for reference in manifest['target_refs'])
