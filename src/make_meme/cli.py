"""make-meme CLI.

  make-meme doctor                 same checks as the check_setup() MCP tool
  make-meme install [recipe ...]   set up ComfyUI + custom nodes + models (default: all recipes)
  make-meme comfy start            run the managed ComfyUI in the foreground
  make-meme comfy proxy            token-protected proxy for exposing ComfyUI remotely
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path


def _doctor() -> int:
    from .server import _check_setup_impl

    report = asyncio.run(_check_setup_impl())
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")

    ffmpeg_ok = bool(report.get("ffmpeg", {}).get("found"))
    ffprobe_ok = bool(report.get("ffprobe", {}).get("found"))
    return 0 if (ffmpeg_ok and ffprobe_ok) else 1


def _install(args: argparse.Namespace) -> int:
    from . import installer
    from .config import get_settings
    from .recipes.loader import all_recipes

    comfy_dir = Path(args.comfy_dir or get_settings().comfy_dir).expanduser()
    profile = args.profile or installer.detect_profile()
    recipes = all_recipes()
    names = args.recipes or sorted(recipes)
    unknown = [n for n in names if n not in recipes]
    if unknown:
        print(f"Unknown recipe(s): {unknown}. Available: {sorted(recipes)}", file=sys.stderr)
        return 2

    print(f"Installing into {comfy_dir} (profile: {profile}): {', '.join(names)}", file=sys.stderr)
    if not args.skip_comfy:
        installer.ensure_comfyui(comfy_dir, use_system_python=args.system_python)
    installer.install_companion_nodes(comfy_dir)
    notes: list[str] = []
    for name in names:
        notes += installer.install_recipe(comfy_dir, recipes[name], profile, skip_models=args.skip_models)
    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    print(
        "Done. Start ComfyUI with `make-meme comfy start` (or point COMFY_URL at your own instance), "
        "then call check_setup from Claude.",
        file=sys.stderr,
    )
    return 0


def _comfy_start(args: argparse.Namespace) -> int:
    from . import installer
    from .config import get_settings

    comfy_dir = Path(args.comfy_dir or get_settings().comfy_dir).expanduser()
    if not (comfy_dir / "main.py").exists():
        print(f"No ComfyUI at {comfy_dir}; run `make-meme install` first.", file=sys.stderr)
        return 1
    profile = args.profile or installer.detect_profile()
    cmd = installer.comfy_launch_command(comfy_dir, port=args.port, listen=args.listen)
    return subprocess.call(cmd, cwd=comfy_dir, env=installer.comfy_env(profile))


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=os.environ.get("MAKE_MEME_LOG", "INFO"), stream=sys.stderr, format="%(message)s")
    parser = argparse.ArgumentParser(prog="make-meme")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check that ffmpeg/ComfyUI/sources are ready to use.")

    p_install = sub.add_parser("install", help="Install ComfyUI, custom nodes and models for recipes.")
    p_install.add_argument("recipes", nargs="*", help="recipe names (default: all)")
    p_install.add_argument("--comfy-dir", help="ComfyUI directory (default: $COMFY_DIR or ~/.make-meme/ComfyUI)")
    p_install.add_argument("--profile", choices=["mps", "cuda", "cuda_lowvram", "cpu"],
                           help="hardware profile (auto-detected)")
    p_install.add_argument("--skip-comfy", action="store_true", help="use an existing ComfyUI as-is")
    p_install.add_argument("--skip-models", action="store_true", help="only install nodes")
    p_install.add_argument("--system-python", action="store_true",
                           help="reuse the current Python's packages (e.g. preinstalled torch in Colab/Kaggle)")

    p_comfy = sub.add_parser("comfy", help="Manage the bundled ComfyUI.")
    comfy_sub = p_comfy.add_subparsers(dest="comfy_command", required=True)
    p_start = comfy_sub.add_parser("start", help="Run ComfyUI in the foreground.")
    p_start.add_argument("--comfy-dir")
    p_start.add_argument("--profile", choices=["mps", "cuda", "cuda_lowvram", "cpu"])
    p_start.add_argument("--port", type=int, default=8188)
    p_start.add_argument("--listen", default="127.0.0.1")
    p_proxy = comfy_sub.add_parser("proxy", help="Token-protected reverse proxy in front of ComfyUI (remote GPUs).")
    p_proxy.add_argument("--upstream", default="http://127.0.0.1:8188")
    p_proxy.add_argument("--port", type=int, default=8189)
    p_proxy.add_argument("--listen", default="127.0.0.1")
    p_proxy.add_argument("--token", help="shared secret (default: random, printed); clients set COMFY_TOKEN")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        sys.exit(_doctor())
    if args.command == "install":
        sys.exit(_install(args))
    if args.command == "comfy" and args.comfy_command == "start":
        sys.exit(_comfy_start(args))
    if args.command == "comfy" and args.comfy_command == "proxy":
        from .comfy import proxy

        token = args.token or proxy.new_token()
        if not args.token:
            print(f"COMFY_TOKEN={token}", file=sys.stderr)
        print(f"proxying http://{args.listen}:{args.port} -> {args.upstream}", file=sys.stderr)
        proxy.serve(args.upstream, args.port, token, host=args.listen)


if __name__ == "__main__":
    main()
