# /// script
# dependencies = []
# ///
# Run after final reports: python3 tools/package_review.py B003_ROOT /tmp/make-meme-B003-review.zip
"""Private small review ZIP with explicit exclusions and CRC/hash readback."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from typing import Final

EXCLUDED_DIRS: Final = {".git", ".venv", "venv", "__pycache__", "models", "weights", "upstream", "cache", ".cache", "latent_cache", "optimizer"}
EXCLUDED_SUFFIXES: Final = {".pt", ".pth", ".safetensors", ".bin", ".ckpt", ".npy", ".npz", ".pem", ".key", ".zip"}
ALLOWED_SUFFIXES: Final = {".py", ".sh", ".md", ".txt", ".json", ".jsonl", ".csv", ".log", ".toml", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".mp4", ".html", ".svg", ".ipynb", ".sha256"}
MAX_FILE: Final = 32_000_000
MAX_PAYLOAD: Final = 280_000_000
MAX_ZIP: Final = 300_000_000


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    root, destination = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    assert destination.parent == Path("/tmp").resolve(), "Use the actual execution host /tmp."
    assert not destination.exists(), "Preserve prior packages; choose a fresh filename."
    included, excluded = [], []
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if path.name in {"ZIP_MANIFEST.json", "ZIP_VERIFICATION.json"}:
            continue
        reason = ""
        if path.is_symlink():
            reason = "symlink"
        elif any(part in EXCLUDED_DIRS for part in relative.parts):
            reason = "environment/model/cache directory"
        elif path.suffix.lower() in EXCLUDED_SUFFIXES or any(token in path.name.lower() for token in ("latent_cache", "optimizer-state", ".env", "credential", "token.secret")):
            reason = "weights/noise/cache/secret artifact"
        elif path.suffix.lower() not in ALLOWED_SUFFIXES:
            reason = "outside explicit review extension allowlist"
        elif path.stat().st_size > MAX_FILE:
            reason = "over32MB: preserve original path/hash instead of embedding"
        if reason:
            excluded.append({"path": str(relative), "bytes": path.stat().st_size, "reason": reason,
                             "sha256": sha(path) if reason.startswith("over32MB") else None})
            continue
        files.append(path)
        included.append({"path": str(relative), "bytes": path.stat().st_size, "sha256": sha(path)})
    total = sum(item["bytes"] for item in included)
    assert total <= MAX_PAYLOAD, "Payload exceeds280MB; do not silently select favorable outputs."
    manifest = {"scope": "PRIVATE review: no public GitHub upload", "root": str(root), "included": included, "excluded": excluded,
                "payload_bytes": total, "limits": {"single_file": MAX_FILE, "payload": MAX_PAYLOAD, "zip": MAX_ZIP}}
    manifest_path = root / "ZIP_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in [*files, manifest_path]:
            archive.write(path, path.relative_to(root))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None, "ZIP CRC failure"
        loaded = json.loads(archive.read("ZIP_MANIFEST.json"))
        assert len(archive.namelist()) == len(loaded["included"]) + 1
        for item in loaded["included"]:
            data = archive.read(item["path"])
            assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
    size = destination.stat().st_size
    result = {"path": str(destination), "bytes": size, "sha256": sha(destination), "crc": "PASS", "all_payload_hashes": "PASS",
              "included_files": len(included), "excluded_files": len(excluded), "within300MB": size <= MAX_ZIP}
    (root / "ZIP_VERIFICATION.json").write_text(json.dumps(result, indent=2) + "\n")
    assert size <= MAX_ZIP, "Oversize ZIP retained with verification record; do not report within budget."
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
