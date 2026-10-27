# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "pillow"]
# ///
"""Parse the fixed two-case image editing contract without altering inputs."""
# Run: imported by qwen_runner.py using the locked B031 environment.
from hashlib import sha256
from pathlib import Path
from typing import Literal
from PIL import Image
from pydantic import BaseModel, ConfigDict

class FileDigest(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: str
    bytes: int

class ImageCase(BaseModel):
    model_config = ConfigDict(frozen=True)
    case_id: Literal['rigid_R1','nonrigid_R1']
    prompt: str
    image_order: tuple[Literal['image1.png'], Literal['image2.png']]
    files: dict[str, FileDigest]

class ImageContract(BaseModel):
    model_config = ConfigDict(frozen=True)
    output_request_wh: tuple[Literal[896], Literal[512]]
    image_seed: Literal[20261026]
    image_steps: Literal[40]
    true_cfg_scale: Literal[4.0]
    guidance_scale: Literal[1.0]
    negative_prompt: Literal[' ']
    image_attempt_limit: Literal[2]
    cases: tuple[ImageCase, ...]

    def checked_images(self, root: Path, case: ImageCase) -> list[Image.Image]:
        """Verify exact original input bytes before local pipeline preprocessing."""
        result = []
        for name in case.image_order:
            path = root/'inputs'/case.case_id/name
            data = path.read_bytes()
            expected = case.files[name]
            assert len(data) == expected.bytes and sha256(data).hexdigest() == expected.sha256
            with Image.open(path) as image:
                result.append(image.convert('RGB'))
        assert result[0].size == (896,512)
        return result

    def check_order(self) -> None:
        """Reject reordered, duplicated or missing cases before any attempt."""
        ids=[case.case_id for case in self.cases]
        assert 1 <= len(ids) <= 2 and len(set(ids))==len(ids)
        assert ids==[name for name in ('rigid_R1','nonrigid_R1') if name in ids]
