from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class DiagramRef:
    source_md: Path
    index: int
    mermaid_src: str
    sha8: str


def _sha8(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def _iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []

    readme = root / "README.md"
    if readme.exists():
        files.append(readme)

    doc_dir = root / "doc"
    if doc_dir.exists():
        files.extend(sorted(doc_dir.rglob("*.md")))

    return files


def _extract_mermaid_blocks(md_text: str, source_md: Path) -> list[DiagramRef]:
    refs: list[DiagramRef] = []
    for i, match in enumerate(MERMAID_BLOCK_RE.finditer(md_text), start=1):
        mermaid_src = match.group(1).strip() + "\n"
        refs.append(
            DiagramRef(
                source_md=source_md,
                index=i,
                mermaid_src=mermaid_src,
                sha8=_sha8(mermaid_src),
            )
        )
    return refs


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stdout: {proc.stdout}\n"
            f"  stderr: {proc.stderr}\n"
        )


def _resolve_npx() -> str:
    # On Windows, `npx` is typically exposed as `npx.cmd`.
    for candidate in ("npx", "npx.cmd", "npx.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(
        "Could not find `npx` on PATH. Install Node.js (which includes npm/npx) and try again."
    )


def _find_browser_executable() -> str | None:
    # Prefer Chrome, fall back to Edge. Used to avoid Puppeteer downloading Chromium.
    candidates: list[str] = []
    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    local_app_data = os.environ.get("LOCALAPPDATA")

    if program_files:
        candidates.append(os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"))
        candidates.append(os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"))
    if program_files_x86:
        candidates.append(os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"))
        candidates.append(os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"))
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"))
        candidates.append(os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"))

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _render_mermaid_to_png(
    repo_root: Path,
    mermaid_src_path: Path,
    png_out_path: Path,
    theme: str,
    background: str,
    scale: float,
    mermaid_cli_pkg: str,
    skip_chromium_download: bool,
    browser_executable: str | None,
) -> None:
    png_out_path.parent.mkdir(parents=True, exist_ok=True)

    npx = _resolve_npx()

    env = os.environ.copy()
    if skip_chromium_download:
        # Prevent Puppeteer from downloading Chromium when mermaid-cli is installed/executed.
        env.setdefault("PUPPETEER_SKIP_DOWNLOAD", "1")
        if browser_executable:
            env.setdefault("PUPPETEER_EXECUTABLE_PATH", browser_executable)

    cmd = [
        npx,
        "-y",
        mermaid_cli_pkg,
        "-i",
        str(mermaid_src_path),
        "-o",
        str(png_out_path),
        "-t",
        theme,
        "-b",
        background,
        "-s",
        str(scale),
    ]

    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stdout: {proc.stdout}\n"
            f"  stderr: {proc.stderr}\n"
        )


def _relpath(from_file: Path, to_file: Path) -> str:
    rel = os.path.relpath(to_file, start=from_file.parent)
    return rel.replace("\\", "/")


def _rewrite_markdown(
    md_text: str,
    source_md: Path,
    diagram_pngs: list[tuple[DiagramRef, Path, Path]],
) -> str:
    # Replace blocks in reverse order to avoid offset issues.
    matches = list(MERMAID_BLOCK_RE.finditer(md_text))
    if not matches:
        return md_text

    if len(matches) != len(diagram_pngs):
        # Conservative: do not rewrite if parsing went sideways.
        return md_text

    new_text = md_text
    for match, (ref, png_path, mmd_path) in zip(reversed(matches), reversed(diagram_pngs)):
        rel_png = _relpath(source_md, png_path)
        rel_mmd = _relpath(source_md, mmd_path)

        replacement = (
            f"![Diagram {ref.index}]({rel_png})\n\n"
            f"Source: [{mmd_path.name}]({rel_mmd})\n"
        )

        start, end = match.span(0)
        new_text = new_text[:start] + replacement + new_text[end:]

    return new_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render Mermaid code blocks in markdown files to PNGs and optionally rewrite markdown "
            "to embed the images."
        )
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repo root (default: current directory).",
    )
    parser.add_argument(
        "--assets-dir",
        default="assets/diagrams",
        help="Where to write PNG and .mmd sources (default: assets/diagrams).",
    )
    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="Rewrite markdown files to replace ```mermaid blocks with embedded PNG + source link.",
    )
    parser.add_argument(
        "--theme",
        default="neutral",
        choices=["neutral", "default", "forest", "dark"],
        help="Mermaid theme (default: neutral).",
    )
    parser.add_argument(
        "--background",
        default="#FFFFFF",
        help="PNG background color (default: #FFFFFF). Use 'transparent' for transparency.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="Render scale factor (default: 2.0).",
    )
    parser.add_argument(
        "--mermaid-cli",
        default="@mermaid-js/mermaid-cli",
        help="npx package for mermaid-cli (default: @mermaid-js/mermaid-cli).",
    )
    parser.add_argument(
        "--allow-chromium-download",
        action="store_true",
        help=(
            "Allow Puppeteer to download Chromium (slow, large). By default we skip the download and "
            "use an installed Chrome/Edge if available."
        ),
    )
    parser.add_argument(
        "--browser",
        default=None,
        help=(
            "Explicit browser executable path for Puppeteer. If omitted, the script will try to find "
            "Chrome or Edge automatically."
        ),
    )

    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    assets_dir = (repo_root / args.assets_dir).resolve()

    browser_executable = args.browser or _find_browser_executable()
    skip_chromium_download = not args.allow_chromium_download

    md_files = _iter_markdown_files(repo_root)
    if not md_files:
        print("No markdown files found.")
        return 0

    total_blocks = 0
    total_rendered = 0
    rewritten_files: list[Path] = []

    for md_path in md_files:
        md_text = md_path.read_text(encoding="utf-8")
        refs = _extract_mermaid_blocks(md_text, md_path)
        if not refs:
            continue

        total_blocks += len(refs)

        diagram_outputs: list[tuple[DiagramRef, Path, Path]] = []
        for ref in refs:
            # Use a stable, collision-resistant name based on content hash.
            stem = md_path.stem
            basename = f"{stem}__diagram_{ref.index:02d}__{ref.sha8}"
            mmd_path = assets_dir / f"{basename}.mmd"
            png_path = assets_dir / f"{basename}.png"

            mmd_path.parent.mkdir(parents=True, exist_ok=True)
            mmd_path.write_text(ref.mermaid_src, encoding="utf-8")

            # Always render, so the PNG stays in sync with the source.
            _render_mermaid_to_png(
                repo_root=repo_root,
                mermaid_src_path=mmd_path,
                png_out_path=png_path,
                theme=args.theme,
                background=args.background,
                scale=args.scale,
                mermaid_cli_pkg=args.mermaid_cli,
                skip_chromium_download=skip_chromium_download,
                browser_executable=browser_executable,
            )
            total_rendered += 1
            diagram_outputs.append((ref, png_path, mmd_path))

        if args.rewrite:
            new_text = _rewrite_markdown(md_text, md_path, diagram_outputs)
            if new_text != md_text:
                md_path.write_text(new_text, encoding="utf-8")
                rewritten_files.append(md_path)

    print(f"Mermaid blocks found: {total_blocks}")
    print(f"Diagrams rendered:   {total_rendered}")
    if args.rewrite:
        print(f"Markdown rewritten:  {len(rewritten_files)}")
        for path in rewritten_files:
            print(f"- {path.relative_to(repo_root).as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
