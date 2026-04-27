"""cli_completion.py

Lightweight, best-effort shell completion support for standalone Python scripts.

Implements:
  --_complete-options
  --print-completion fish|zsh
  install-completion fish|zsh
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def _cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "cli-completions"


def _cmd_name(argv0: str) -> str:
    return os.path.basename(argv0)


def _sanitize_ident(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _run_help(argv0: str) -> str:
    for args in (["--help"], ["-h"], ["help"]):
        try:
            r = subprocess.run(
                [argv0, *args],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
        except Exception:
            continue
        if r.stdout.strip():
            return r.stdout
    return ""


def _extract_opts_from_text(text: str) -> list[str]:
    tokens = re.findall(r"(?<![\w-])(--[A-Za-z0-9][A-Za-z0-9_-]*|-[A-Za-z0-9])", text)
    out: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        if t in ("--_complete-options",):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _extract_opts_cached(argv0: str) -> list[str]:
    cmd_name = _cmd_name(argv0)
    cache_file = _cache_dir() / f"{cmd_name}.opts"
    try:
        cmd_mtime = Path(argv0).stat().st_mtime
    except OSError:
        cmd_mtime = 0

    try:
        if cache_file.exists() and cache_file.stat().st_mtime >= cmd_mtime:
            lines = [ln.strip() for ln in cache_file.read_text().splitlines() if ln.strip()]
            if lines:
                return lines
    except OSError:
        pass

    text = _run_help(argv0)
    opts = _extract_opts_from_text(text)
    if opts:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text("\n".join(opts) + "\n")
        except OSError:
            pass
    return opts


def _print_fish(cmd_name: str) -> str:
    fn = _sanitize_ident(f"__{cmd_name}_complete_opts")
    return (
        f"function {fn}\n"
        f"    {cmd_name} --_complete-options 2>/dev/null\n"
        f"end\n\n"
        f"complete -c {cmd_name} -f -a \"({fn})\"\n"
    )


def _print_zsh(cmd_name: str) -> str:
    return (
        f"#compdef {cmd_name}\n\n"
        "local -a opts\n"
        f"opts=(${{(f)\"$({cmd_name} --_complete-options 2>/dev/null)\"}})\n\n"
        "compadd -a opts\n"
    )


def maybe_handle(argv0: str, argv: Sequence[str]) -> None:
    if len(argv) < 2:
        return

    cmd_name = _cmd_name(argv0)
    sub = argv[1]

    if sub == "--_complete-options":
        for opt in _extract_opts_cached(argv0):
            print(opt)
        raise SystemExit(0)

    if sub == "--print-completion":
        if len(argv) < 3 or argv[2] not in ("fish", "zsh"):
            print(f"Usage: {cmd_name} --print-completion {{fish|zsh}}", file=sys.stderr)
            raise SystemExit(2)
        print(_print_fish(cmd_name) if argv[2] == "fish" else _print_zsh(cmd_name), end="")
        raise SystemExit(0)

    if sub == "install-completion":
        if len(argv) < 3 or argv[2] not in ("fish", "zsh"):
            print(f"Usage: {cmd_name} install-completion {{fish|zsh}}", file=sys.stderr)
            raise SystemExit(2)

        if argv[2] == "fish":
            out_dir = Path.home() / ".config" / "fish" / "completions"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{cmd_name}.fish"
            out_file.write_text(_print_fish(cmd_name))
            print(str(out_file), file=sys.stderr)
            raise SystemExit(0)

        out_dir = Path.home() / ".zsh" / "completions"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"_{cmd_name}"
        out_file.write_text(_print_zsh(cmd_name))
        print(str(out_file), file=sys.stderr)
        raise SystemExit(0)
