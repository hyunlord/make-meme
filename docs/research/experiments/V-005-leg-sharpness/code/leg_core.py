# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy"]
# ///
"""CPU numerical core. Run tests with existing Python: -m pytest test_leg_core.py."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TypedDict
import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import convolve, distance_transform_edt

Mask = NDArray[np.bool_]
Pixels = NDArray[np.uint8]

@dataclass(frozen=True, slots=True)
class Policy:
    master_size: tuple[int,int]
    role: str
    lower_fraction: float
    mask_dilation_px: int
    boundary_band_px: int
    gray: tuple[float,float]
    dark_max: float
    luma_weights: tuple[float,float,float]
    laplacian_kernel: tuple[tuple[float,...],...]
    laplacian_border: str
    window: tuple[int,int]
    local_dilation_px: int
    local_feather_px: int
    ramp_in: tuple[int,int]
    ramp_out: tuple[int,int]

class FrameScore(TypedDict):
    status: str
    region_pixels: int
    boundary_pixels: int
    gray_pixels: int
    dark_pixels: int
    semi_transparency_ratio: float | None
    edge_laplacian_variance: float | None

class Summary(TypedDict):
    observed: int
    total: int
    mean: float | None
    maximum: float | None

class MetricSummary(TypedDict):
    window: Summary
    outside: Summary
    window_mean_over_outside_mean: float | None


def dilate(mask: Mask, radius: int) -> Mask:
    """Euclidean disk, including the input mask; empty stays empty."""
    return distance_transform_edt(~mask)<=radius if mask.any() else mask.copy()


def lower_box(mask: Mask, fraction: float) -> Mask:
    """Half-open bbox; first lower row is ceil(ymax - fraction * height)."""
    result=np.zeros_like(mask)
    if mask.any():
        ys,xs=np.nonzero(mask)
        y0,y1=int(ys.min()),int(ys.max()+1)
        top=int(np.ceil(y1-fraction*(y1-y0)))
        result[top:y1,int(xs.min()):int(xs.max()+1)]=True
    return result


def leg_region(body: Mask, reflection: Mask, valid: Mask, policy: Policy) -> Mask:
    """Use lower bbox intersect dilated real body, excluding reflections/crop loss."""
    return lower_box(body,policy.lower_fraction)&dilate(body,policy.mask_dilation_px)&~reflection&valid


def frame_metrics(rgb: Pixels, body: Mask | None, reflection: Mask, valid: Mask,
                  policy: Policy) -> FrameScore:
    """Compute unrounded Rec601 luma ratio and configured Laplacian variance."""
    result: FrameScore={'status':'MISSING_LAB','region_pixels':0,'boundary_pixels':0,
                       'gray_pixels':0,'dark_pixels':0,'semi_transparency_ratio':None,
                       'edge_laplacian_variance':None}
    if body is None or not body.any():
        return result
    region=leg_region(body,reflection,valid,policy)
    inside=distance_transform_edt(np.pad(region,1))[1:-1,1:-1]
    band=dilate(region,policy.boundary_band_px)&(inside<=policy.boundary_band_px)&valid&~reflection
    luma=rgb.astype(np.float64)@np.asarray(policy.luma_weights)
    grey=int(((luma>=policy.gray[0])&(luma<=policy.gray[1])&region).sum())
    dark=int(((luma<policy.dark_max)&region).sum())
    lap=convolve(luma,np.asarray(policy.laplacian_kernel),mode=policy.laplacian_border)
    result.update(status='MEASURED' if region.any() else 'EMPTY_REGION',region_pixels=int(region.sum()),
                  boundary_pixels=int(band.sum()),gray_pixels=grey,dark_pixels=dark,
                  semi_transparency_ratio=grey/(grey+dark) if grey+dark else None,
                  edge_laplacian_variance=float(lap[band].var()) if band.any() else None)
    return result


def local_alpha(body: Mask | None, frame: int, policy: Policy) -> NDArray[np.float64]:
    """Lower bbox dilation then finite inward feather and inclusive linear ramps."""
    shape=body.shape if body is not None else (policy.master_size[1],policy.master_size[0])
    if body is None or not body.any() or not policy.ramp_in[0]<=frame<=policy.ramp_out[1]:
        return np.zeros(shape,dtype=np.float64)
    temporal=min(1.,(frame-policy.ramp_in[0])/(policy.ramp_in[1]-policy.ramp_in[0]),
                 (policy.ramp_out[1]-frame)/(policy.ramp_out[1]-policy.ramp_out[0]))
    region=dilate(lower_box(body,policy.lower_fraction),policy.local_dilation_px)
    distance=distance_transform_edt(np.pad(region,1))[1:-1,1:-1]
    return np.clip(distance/policy.local_feather_px,0,1)*temporal


def blend(base: Pixels, refined: Pixels, alpha: NDArray[np.float64]) -> Pixels:
    """Round to nearest uint8; alpha-zero exterior equals base bytes exactly."""
    result=np.rint(base*(1-alpha[:,:,None])+refined*alpha[:,:,None]).astype(np.uint8)
    result[alpha==0]=base[alpha==0]
    result[alpha==1]=refined[alpha==1]
    return result


def stats(values: list[float | None]) -> Summary:
    """Observed-only stats with mandatory coverage; missing is never zero."""
    present=[v for v in values if v is not None]
    return {'observed':len(present),'total':len(values),'mean':float(np.mean(present)) if present else None,
            'maximum':float(max(present)) if present else None}


def summarize(rows: list[dict], policy: Policy) -> dict[str,MetricSummary]:
    """Window/outside metrics and ratio with undefined denominator retained null."""
    result={}
    for name in ('semi_transparency_ratio','edge_laplacian_variance'):
        window=stats([r[name] for r in rows if policy.window[0]<=r['frame']<=policy.window[1]])
        outside=stats([r[name] for r in rows if not policy.window[0]<=r['frame']<=policy.window[1]])
        ratio=window['mean']/outside['mean'] if window['mean'] is not None and outside['mean'] not in (None,0) else None
        result[name]={'window':window,'outside':outside,'window_mean_over_outside_mean':ratio}
    return result
