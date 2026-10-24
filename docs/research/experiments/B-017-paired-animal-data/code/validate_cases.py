# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2,<3"]
# ///
"""Usage: python validate_cases.py PRIVATE_MANIFEST --output PRIVATE_REPORT."""
import argparse
from itertools import combinations
from pathlib import Path

from case_schema import Asset, Case, Frozen, Manifest
from media_check import MediaReport, inspect_media


class CaseReport(Frozen):
    sample_id: str
    pair_type: str
    media: dict[str, MediaReport]
    missing_fields: tuple[str, ...]
    blockers: tuple[str, ...]
    structural_media_complete: bool
    pair_available: bool
    r_y_source_temporal_overlap: bool | None
    d_y_source_temporal_overlap: bool | None
    training_ready: bool
    readiness: tuple[str, ...]
    d_equals_y_file: bool | None
    d_equals_y_decoded: bool | None
    r_equals_y_first_decoded: bool | None
    r_equals_y_first_source_lineage: bool | None


class Report(Frozen):
    schema_version: int = 1
    cases: tuple[CaseReport, ...]
    leakage_flags: tuple[str, ...]
    claims: tuple[str, ...] = ('CPU_MEDIA_CHECK_ONLY', 'IDENTITY_AND_MOTION_EVIDENCE_DECLARED',
                              'NO_TRAINING_OR_ANIMAL_QUALITY_VALIDATION')


def assets(case: Case) -> dict[str, Asset | None]:
    return {'R': case.R, 'D': case.D, 'Y': case.Y,
            'masks.R': case.masks.R, 'masks.D': case.masks.D}


def split_leakage(cases: tuple[Case, ...]) -> tuple[str, ...]:
    flags: list[str] = []
    for one, two in combinations(cases, 2):
        if one.split == two.split:
            continue
        prefix = f'{one.sample_id}/{two.sample_id}'
        if one.origin_group == two.origin_group:
            flags.append(f'{prefix}:ORIGIN_GROUP_CROSS_SPLIT')
        for left in (one.R, one.D, one.Y):
            for right in (two.R, two.D, two.Y):
                if left is None or right is None:
                    continue
                if left.identity_id and left.identity_id == right.identity_id:
                    flags.append(f'{prefix}:IDENTITY_CROSS_SPLIT')
                if left.session_id == right.session_id:
                    flags.append(f'{prefix}:SESSION_CROSS_SPLIT')
                ancestors_left = {left.source_id, *left.parent_ids}
                ancestors_right = {right.source_id, *right.parent_ids}
                if ancestors_left & ancestors_right:
                    flags.append(f'{prefix}:SOURCE_CROSS_SPLIT')
                if left.source_id == right.source_id and max(left.frame_indices[0], right.frame_indices[0]) <= min(left.frame_indices[-1], right.frame_indices[-1]):
                    flags.append(f'{prefix}:TEMPORAL_OVERLAP')
    return tuple(sorted(set(flags)))


def pair_blockers(case: Case) -> list[str]:
    blocks: list[str] = []
    if case.R is None or case.D is None or case.Y is None:
        return ['PAIR_ASSETS_MISSING']
    if case.identity_evidence.status != 'CONFIRMED' or not case.identity_evidence.basis:
        blocks.append('R_Y_IDENTITY_UNCONFIRMED')
    if not case.R.identity_id or case.R.identity_id != case.Y.identity_id:
        blocks.append('R_Y_IDENTITY_MISMATCH_OR_UNKNOWN')
    match case.pair_type:
        case 'SELF_RECON_SMOKE':
            if not case.D.identity_id or case.D.identity_id != case.Y.identity_id:
                blocks.append('SELF_D_Y_IDENTITY_MISMATCH_OR_UNKNOWN')
        case 'SAME_ID_POSE_VARIATION':
            if not case.D.identity_id or case.D.identity_id != case.Y.identity_id:
                blocks.append('SAME_ID_D_Y_IDENTITY_MISMATCH_OR_UNKNOWN')
            if case.reference_pose_evidence.status != 'CONFIRMED' or not case.reference_pose_evidence.basis:
                blocks.append('POSE_VARIATION_UNCONFIRMED')
        case 'CROSS_ID_MOTION_PAIR':
            if not case.D.identity_id or case.D.identity_id == case.Y.identity_id:
                blocks.append('CROSS_ID_D_Y_DISTINCTION_UNCONFIRMED')
            if case.motion_correspondence.status != 'CONFIRMED' or not case.motion_correspondence.basis:
                blocks.append('MOTION_CORRESPONDENCE_UNCONFIRMED')
    return blocks


def temporal_overlap(left: Asset | None, right: Asset | None) -> bool | None:
    if left is None or right is None or left.source_id != right.source_id:
        return None
    return max(left.frame_indices[0], right.frame_indices[0]) <= min(left.frame_indices[-1], right.frame_indices[-1])


def validate_case(case: Case, base: Path, leaked: bool) -> CaseReport:
    media: dict[str, MediaReport] = {}
    missing: list[str] = []
    for name, asset in assets(case).items():
        if asset is None:
            missing.append(name)
        else:
            resolved = asset.model_copy(update={'path': base / asset.path})
            media[name] = inspect_media(resolved)
    if not case.caption.strip():
        missing.append('caption')
    blocks = pair_blockers(case)
    if case.R and case.R.kind != 'IMAGE':
        blocks.append('REFERENCE_MUST_BE_IMAGE')
    if any(asset.kind != 'VIDEO' for asset in (case.D, case.Y) if asset is not None):
        blocks.append('DRIVING_TARGET_MUST_BE_VIDEO')
    d_report, y_report = media.get('D'), media.get('Y')
    if (case.pair_type != 'CROSS_ID_MOTION_PAIR' and d_report and y_report
            and d_report.frame_sha256 != y_report.frame_sha256
            and case.motion_correspondence.status != 'CONFIRMED'):
        blocks.append('SELF_D_Y_ALIGNMENT_UNCONFIRMED')
    if (case.pair_type == 'CROSS_ID_MOTION_PAIR' and d_report and y_report
            and d_report.status == y_report.status == 'PASS'
            and d_report.frame_sha256 == y_report.frame_sha256):
        blocks.append('CROSS_ID_PIXEL_IDENTICAL_SHORTCUT')
    if missing:
        blocks.append('ASSETS_MISSING')
    if any(report.status != 'PASS' for report in media.values()):
        blocks.append('MEDIA_VALIDATION_FAILED')
    for name in ('R', 'D'):
        rgb, mask = assets(case)[name], assets(case)[f'masks.{name}']
        if rgb and mask and (rgb.width, rgb.height, rgb.frames, rgb.fps, rgb.timestamps, rgb.frame_indices) != (mask.width, mask.height, mask.frames, mask.fps, mask.timestamps, mask.frame_indices):
            blocks.append(f'MASK_{name}_SPATIAL_TEMPORAL_MISMATCH')
        if rgb and mask and (rgb.source_id, rgb.session_id) != (mask.source_id, mask.session_id):
            blocks.append(f'MASK_{name}_SOURCE_LINEAGE_MISMATCH')
    structural_complete = (not missing and all(item.status == 'PASS' for item in media.values())
                           and not any(block.startswith(('MASK_', 'REFERENCE_MUST_', 'DRIVING_TARGET_')) for block in blocks))
    if case.Y and case.Y.origin != 'REAL':
        blocks.append('GENERATED_TARGET_EXCLUDED' if case.Y.origin == 'GENERATED' else 'TARGET_ORIGIN_UNKNOWN')
    available = not blocks
    if leaked:
        blocks.append('CROSS_SPLIT_LEAKAGE')
    if case.rights.training != 'ALLOWED' or not case.rights.permission_id:
        blocks.append('TRAINING_RIGHTS_UNCONFIRMED')
    if case.rights.research != 'ALLOWED':
        blocks.append('RESEARCH_RIGHTS_UNCONFIRMED')
    readiness: list[str] = []
    if available:
        readiness.append({'SELF_RECON_SMOKE': 'SMOKE_DATA_READY',
                          'SAME_ID_POSE_VARIATION': 'POSE_VARIATION_AVAILABLE',
                          'CROSS_ID_MOTION_PAIR': 'CROSS_ID_PAIR_AVAILABLE'}[case.pair_type])
    else:
        readiness.append('DATA_GAP')
    if any('RIGHTS' in block for block in blocks):
        readiness.append('RIGHTS_PENDING')
    driving, target, reference = media.get('D'), media.get('Y'), media.get('R')
    dy_file = dy_decoded = ry_decoded = ry_lineage = None
    if driving and target and driving.status == target.status == 'PASS':
        dy_file = driving.file_sha256 == target.file_sha256
        dy_decoded = driving.frame_sha256 == target.frame_sha256
    if reference and target and reference.status == target.status == 'PASS':
        ry_decoded = reference.frame_sha256[0] == target.frame_sha256[0]
    if case.R and case.Y:
        ry_lineage = case.R.source_id == case.Y.source_id and case.R.frame_indices[0] == case.Y.frame_indices[0]
    return CaseReport(sample_id=case.sample_id, pair_type=case.pair_type, media=media,
                      missing_fields=tuple(missing), blockers=tuple(blocks),
                      structural_media_complete=structural_complete,
                      r_y_source_temporal_overlap=temporal_overlap(case.R, case.Y),
                      d_y_source_temporal_overlap=temporal_overlap(case.D, case.Y),
                      pair_available=available, training_ready=not blocks,
                      readiness=tuple(readiness), d_equals_y_file=dy_file,
                      d_equals_y_decoded=dy_decoded, r_equals_y_first_decoded=ry_decoded,
                      r_equals_y_first_source_lineage=ry_lineage)


def validate_manifest(manifest: Manifest, base: Path | None = None) -> Report:
    base = Path('.') if base is None else base
    leakage = split_leakage(manifest.cases)
    return Report(cases=tuple(validate_case(case, base, any(case.sample_id in flag.split(':')[0].split('/') for flag in leakage))
                              for case in manifest.cases), leakage_flags=leakage)


class CLI(argparse.Namespace):
    def __init__(self) -> None:
        super().__init__()
        self.manifest: Path = Path('.')
        self.output: Path = Path('.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument('manifest', type=Path)
    _ = parser.add_argument('--output', type=Path, required=True)
    args = CLI()
    _ = parser.parse_args(namespace=args)
    manifest_path = Path(args.manifest)
    report = validate_manifest(Manifest.model_validate_json(manifest_path.read_text()), manifest_path.parent)
    _ = Path(args.output).write_text(report.model_dump_json(indent=2) + '\n')


if __name__ == '__main__':
    main()
