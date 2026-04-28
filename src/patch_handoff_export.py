from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.common import ROOT, resolve_repo_path
from src.handoff_bundle import HandoffBundleResult, is_forbidden_entry, normalize_entry_name, omitted_row
from src.handoff_zip_export import export_profile_handoff_zip


@dataclass(frozen=True)
class PatchHandoffExportResult:
    zip_path: Path
    patch_id: str
    branch: str
    head: str
    short_head: str
    file_count: int
    size_bytes: int
    sha256: str
    included_entries: tuple[str, ...]


def is_forbidden_patch_handoff_entry(entry_name: str) -> bool:
    return is_forbidden_entry(entry_name)


def export_patch_handoff_zip(
    *,
    patch_id: str,
    include_paths: Iterable[str | Path],
    repo_root: str | Path = ROOT,
    output_dir: str | Path | None = None,
    summary: str = "",
    validation: str = "",
    omitted_private_entries: Iterable[str] = (),
) -> PatchHandoffExportResult:
    root = resolve_repo_path(repo_root).resolve()
    includes: list[str] = []
    forbidden: list[str] = []
    for path_value in include_paths:
        path = resolve_repo_path(path_value).resolve()
        try:
            rel_name = normalize_entry_name(path.relative_to(root).as_posix())
        except ValueError:
            rel_name = normalize_entry_name(path_value)
        includes.append(rel_name)
        if is_forbidden_entry(rel_name):
            forbidden.append(rel_name)
    if forbidden:
        raise ValueError(f"patch handoff include path is forbidden: {', '.join(forbidden)}")
    # Compatibility wrapper only: all archive creation, manifest, guardrail and
    # validation logic lives in src.handoff_bundle via handoff_zip_export.
    result: HandoffBundleResult = export_profile_handoff_zip(
        profile="patch",
        name=patch_id,
        repo_root=repo_root,
        output_dir=output_dir,
        include_paths=includes,
        validation_summary=validation or summary,
    )
    if omitted_private_entries:
        # The unified profile already records default private omissions. This
        # keeps the old argument visible to callers without reimplementing zip logic.
        _ = [omitted_row(str(entry), "OMITTED_PRIVATE", "False", "False", "True", "Compatibility wrapper omission.") for entry in omitted_private_entries]
    return PatchHandoffExportResult(
        zip_path=result.zip_path,
        patch_id=patch_id,
        branch=result.branch,
        head=result.head,
        short_head=result.short_head,
        file_count=result.file_count,
        size_bytes=result.size_bytes,
        sha256=result.sha256,
        included_entries=result.included_entries,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compatibility wrapper for unified patch handoff export.")
    parser.add_argument("--patch-id", required=True)
    parser.add_argument("--include-path", action="append", default=[], help="Repo-relative file to include; repeatable.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--validation", default="")
    parser.add_argument("--omitted-private-entry", action="append", default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = export_patch_handoff_zip(
        patch_id=args.patch_id,
        include_paths=args.include_path,
        repo_root=args.repo_root,
        output_dir=args.output_dir or None,
        summary=args.summary,
        validation=args.validation,
        omitted_private_entries=args.omitted_private_entry,
    )
    print(f"zip_path={result.zip_path}")
    print(f"patch_id={result.patch_id}")
    print(f"head={result.head}")
    print(f"file_count={result.file_count}")
    print(f"size_bytes={result.size_bytes}")
    print(f"sha256={result.sha256}")


if __name__ == "__main__":
    main()
