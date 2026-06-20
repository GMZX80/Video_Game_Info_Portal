from __future__ import annotations

import argparse
from typing import Any

from scripts import build_all as build_pipeline
from scripts.ingest import archive_postprocess, sinclair_supplement, sinclair_user, stairway, stairway_supplement
from scripts.ingest.common import DEFAULT_ACCESSED_AT


def run(
    *,
    resume: bool = False,
    include_catalogues: bool = False,
    max_pages: int = 0,
    accessed_at: str = DEFAULT_ACCESSED_AT,
) -> dict[str, Any]:
    """Run the supported external detailed-ingest workflow.

    Normal CI must keep using `python -m scripts.build_all --skip-fetch`.
    This entry point intentionally performs external requests and then rebuilds
    from the committed raw records it just refreshed.
    """

    sinclair_counts = sinclair_user.run(
        indexes_only=False,
        resume=resume,
        accessed_at=accessed_at,
        max_pages=max_pages,
    )
    sinclair_supplement_counts = sinclair_supplement.supplement(accessed_at=accessed_at)
    stairway_counts = stairway.run(
        indexes_only=False,
        resume=resume,
        accessed_at=accessed_at,
        max_pages=max_pages,
        include_catalogues=include_catalogues,
    )
    stairway_supplement_counts = stairway_supplement.supplement(accessed_at=accessed_at)
    sinclair_postprocess = archive_postprocess.clean_sinclair_supplement()
    photo_postprocess = archive_postprocess.capture_tynesoft_photo_testimony(accessed_at=accessed_at)
    build_counts = build_pipeline.build_all(skip_fetch=True)
    media_assets = archive_postprocess.merge_curated_media()
    archive_postprocess.write_audit(photo_postprocess, sinclair_postprocess)

    return {
        "sinclair_user": sinclair_counts,
        "sinclair_supplement": sinclair_supplement_counts,
        "stairway": stairway_counts,
        "stairway_supplement": stairway_supplement_counts,
        "postprocess": {
            **sinclair_supplement_counts,
            **stairway_supplement_counts,
            **sinclair_postprocess,
            **photo_postprocess,
            "media_assets": media_assets,
        },
        "build": build_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the detailed Sinclair User and Stairway To Hell archive refresh.")
    parser.add_argument("--resume", action="store_true", help="Reuse cached archive responses where available.")
    parser.add_argument("--include-catalogues", action="store_true", help="Include Stairway BBC/Electron HTML catalogue pages; binaries remain excluded.")
    parser.add_argument("--max-pages", type=int, default=0, help="Optional page limit per archive; zero means no explicit limit.")
    parser.add_argument("--accessed-date", default=DEFAULT_ACCESSED_AT)
    args = parser.parse_args()
    print(
        run(
            resume=args.resume,
            include_catalogues=args.include_catalogues,
            max_pages=args.max_pages,
            accessed_at=args.accessed_date,
        )
    )


if __name__ == "__main__":
    main()
