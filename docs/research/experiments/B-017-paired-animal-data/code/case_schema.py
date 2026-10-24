"""Private input contract. Evidence declarations are not automated identity proof."""
from pathlib import Path
from typing import Annotated, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal['CONFIRMED', 'UNKNOWN', 'CONTRADICTED']
Permission = Literal['ALLOWED', 'UNKNOWN', 'DENIED']
PairType = Literal['SELF_RECON_SMOKE', 'SAME_ID_POSE_VARIATION', 'CROSS_ID_MOTION_PAIR']


class Frozen(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra='forbid', allow_inf_nan=False)


class Evidence(Frozen):
    status: Status = 'UNKNOWN'
    basis: str = ''


class Rights(Frozen):
    research: Permission = 'UNKNOWN'
    training: Permission = 'UNKNOWN'
    redistribution: Permission = 'UNKNOWN'
    commercial: Permission = 'UNKNOWN'
    permission_id: str = ''


class Asset(Frozen):
    path: Path
    kind: Literal['IMAGE', 'VIDEO']
    width: Annotated[int, Field(gt=0, le=4096)]
    height: Annotated[int, Field(gt=0, le=4096)]
    frames: Annotated[int, Field(gt=0, le=240)]
    fps: Annotated[float, Field(gt=0, le=120)]
    timestamps: tuple[float, ...]
    source_id: Annotated[str, Field(min_length=1)]
    session_id: Annotated[str, Field(min_length=1)]
    identity_id: str | None = None
    source_fps: Annotated[float, Field(gt=0, le=120)]
    frame_indices: tuple[int, ...]
    origin: Literal['REAL', 'GENERATED', 'UNKNOWN'] = 'UNKNOWN'
    parent_ids: tuple[str, ...] = ()

    @model_validator(mode='after')
    def consistent(self) -> Self:
        if len(self.timestamps) != self.frames or len(self.frame_indices) != self.frames:
            raise ValueError('timestamps and frame_indices must cover every frame')
        if self.kind == 'IMAGE' and self.frames != 1:
            raise ValueError('IMAGE requires exactly one frame')
        if any(i < 0 for i in self.frame_indices):
            raise ValueError('source frame indices must be nonnegative')
        if any(b <= a for a, b in zip(self.timestamps, self.timestamps[1:])):
            raise ValueError('encoded timestamps must strictly increase')
        if any(b <= a for a, b in zip(self.frame_indices, self.frame_indices[1:])):
            raise ValueError('source indices must strictly increase; no duplicated samples')
        return self


class Masks(Frozen):
    R: Asset | None = None
    D: Asset | None = None


class Case(Frozen):
    sample_id: Annotated[str, Field(pattern=r'^[A-Za-z0-9_.-]+$')]
    pair_type: PairType
    R: Asset | None = None
    D: Asset | None = None
    Y: Asset | None = None
    masks: Masks = Field(default_factory=Masks)
    identity_evidence: Evidence = Field(default_factory=Evidence)
    motion_correspondence: Evidence = Field(default_factory=Evidence)
    reference_pose_evidence: Evidence = Field(default_factory=Evidence)
    rights: Rights = Field(default_factory=Rights)
    origin_group: str
    split: Literal['DEVELOPMENT', 'TRAIN', 'VALIDATION', 'TEST']
    mode: Literal['ANIMATION', 'REPLACEMENT']
    caption: str
    motion_id: str = ''
    reference_pose: str = ''
    target_pose: str = ''
    scene_id: str = ''
    event_times: tuple[float, ...] = ()


class Manifest(Frozen):
    schema_version: Literal[1] = 1
    cases: Annotated[tuple[Case, ...], Field(min_length=1, max_length=8)]

    @model_validator(mode='after')
    def unique(self) -> Self:
        if len({case.sample_id for case in self.cases}) != len(self.cases):
            raise ValueError('sample_id must be unique')
        return self
