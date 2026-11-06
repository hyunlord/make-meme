# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "Pillow"]
# ///
"""CPU geometry and fixed casting I/O for leg_metrics.py and leg_local.py."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import numpy as np
from numpy.typing import NDArray
from PIL import Image
from leg_core import Policy, Mask, Pixels


def read_policy(scene: Path) -> Policy:
    """Read numerical definitions from the preregistered effective scene config."""
    p=json.loads(scene.read_text())['measurement_policy']
    return Policy(tuple(p['master_size']),p['role'],float(p['lower_fraction']),int(p['mask_dilation_px']),
                  int(p['boundary_band_px']),tuple(p['gray_luma_inclusive']),float(p['dark_luma_exclusive_max']),
                  tuple(p['luma_rgb_weights']),tuple(tuple(row) for row in p['laplacian_kernel']),
                  p['laplacian_border'],tuple(p['window_inclusive']),int(p['local_dilation_px']),
                  int(p['local_feather_px']),tuple(p['local_ramp_in']),tuple(p['local_ramp_out']))

@dataclass(frozen=True, slots=True)
class Canvas:
    master: tuple[int,int]
    native: tuple[int,int]

    @property
    def resized(self) -> tuple[int,int]:
        scale=max(self.native[0]/self.master[0],self.native[1]/self.master[1])
        return round(self.master[0]*scale),round(self.master[1]*scale)

    @property
    def offset(self) -> tuple[int,int]:
        return (self.resized[0]-self.native[0])//2,(self.resized[1]-self.native[1])//2

    def to_master(self, image: Image.Image, *, mask: bool=False) -> Image.Image:
        """Inverse center crop via zero padding; consumers exclude missing crop rows."""
        if image.size==self.master:
            return image.copy()
        if image.size!=self.native:
            raise ValueError(f'Unexpected image size {image.size}; expected {self.master} or {self.native}')
        padded=Image.new(image.mode,self.resized)
        padded.paste(image,self.offset)
        return padded.resize(self.master,Image.Resampling.NEAREST if mask else Image.Resampling.BICUBIC)

    def valid(self) -> Mask:
        """Observed native field of view in master coordinates."""
        return np.asarray(self.to_master(Image.new('L',self.native,255),mask=True))>0

    def alpha_native(self, alpha: NDArray[np.float64]) -> NDArray[np.float64]:
        """Project an alpha field to native pixels without changing original RGB."""
        image=Image.fromarray(alpha.astype(np.float32)).resize(self.resized,Image.Resampling.BILINEAR)
        x,y=self.offset
        return np.asarray(image.crop((x,y,x+self.native[0],y+self.native[1])),dtype=np.float64)


def rgb_master(path: Path, canvas: Canvas) -> Pixels:
    with Image.open(path) as image:
        return np.asarray(canvas.to_master(image.convert('RGB')),dtype=np.uint8)


def rgb_native(path: Path, canvas: Canvas) -> Pixels:
    with Image.open(path) as image:
        if image.size!=canvas.native:
            raise ValueError(f'Local composite requires byte-preserving native inputs: {path}')
        return np.asarray(image.convert('RGB'),dtype=np.uint8)


def read_masks(summary: Path, frame: int, canvas: Canvas) -> dict[int,Mask]:
    """Load only present masks from actual SAM summary; no inference or recasting."""
    data=json.loads(summary.read_text())
    row=next(row for row in data['frames'] if row['index']==frame)
    result={}
    for obj in row['objects']:
        if obj['present']:
            track=int(obj['track_index'])
            with Image.open(summary.parent/f'{frame:03d}-track-{track:02d}.png') as image:
                if tuple(data['coordinate_size'])!=image.size:
                    raise ValueError('SAM summary canvas mismatch')
                result[track]=np.asarray(canvas.to_master(image.convert('L'),mask=True))>0
    return result


def fixed_body(base: dict, row: dict, masks: dict[int,Mask], role: str) -> Mask | None:
    """Follow saved first-frame casting; a reflected/missing track is not a body."""
    casting=base.get('casting')
    target=casting.get(role) if casting else None
    if base.get('casting_status')!='ESTABLISHED' or target not in row['actual_tracks']:
        return None
    return masks.get(target)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, data: dict) -> None:
    """New-file only, atomic replace and JSON readback."""
    if path.exists():
        raise FileExistsError(path)
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('x') as stream:
        json.dump(data,stream,indent=2,allow_nan=False)
        stream.write('\n')
    json.loads(temporary.read_text())
    temporary.replace(path)
