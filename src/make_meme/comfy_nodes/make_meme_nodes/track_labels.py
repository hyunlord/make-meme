"""MakeMemeTrackLabels: SAM 3 video tracks as one label image per frame.

ComfyUI's SAM3_TrackToMask unions the selected objects, which loses who is who. This
node keeps the tracker's object identities: pixel value k/255 (in every channel) means
"object k-1", 0 means background. Object indices are stable across frames; objects the
tracker detects later get new indices. Saved through SaveImage, labels round-trip
exactly through 8-bit PNG.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


class MakeMemeTrackLabels:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"track_data": ("SAM3_TRACK_DATA", {})}}

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "labels"
    CATEGORY = "make-meme"

    def labels(self, track_data):
        from comfy.ldm.sam3.tracker import unpack_masks

        packed = track_data["packed_masks"]
        h, w = track_data["orig_size"]
        n = track_data["n_frames"]
        if packed is None:
            return (torch.zeros(n, h, w, 3),)
        n_obj = min(packed.shape[1], 254)
        frames = []
        for i in range(packed.shape[0]):  # frame by frame: N x objects x H x W at once is too big
            masks = unpack_masks(packed[i, :n_obj]).unsqueeze(1).float()  # [objects, 1, Hm, Wm]
            masks = F.interpolate(masks, size=(h, w), mode="bilinear", align_corners=False)[:, 0] > 0.5
            ids = torch.arange(1, n_obj + 1, device=masks.device).view(-1, 1, 1)
            # Overlaps go to the lower index (the object tracked first).
            label = torch.where(masks, ids, torch.full_like(ids, 255)).min(dim=0).values
            label = torch.where(label == 255, torch.zeros_like(label), label)
            frames.append(label.float().cpu() / 255.0)
        out = torch.stack(frames).unsqueeze(-1).repeat(1, 1, 1, 3)
        return (out,)
