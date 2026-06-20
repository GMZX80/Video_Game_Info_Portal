def test_run_detailed_orchestrates_archives_postprocess_and_rebuild(monkeypatch):
    from scripts.ingest import run_detailed

    calls = []

    def fake_sinclair(**kwargs):
        calls.append(("sinclair", kwargs))
        return {"issues": 133, "source_items": 5176}

    def fake_stairway(**kwargs):
        calls.append(("stairway", kwargs))
        return {"issues": 0, "source_items": 801}

    def fake_sinclair_supplement(**kwargs):
        calls.append(("sinclair_supplement", kwargs))
        return {"physical_issue_pages_discovered": 133, "unlinked_software_entries_added": 3845}

    def fake_stairway_supplement(**kwargs):
        calls.append(("stairway_supplement", kwargs))
        return {"catalogue_navigation_rows_removed": 27, "remaining_failures": 0}

    def fake_clean():
        calls.append(("clean_sinclair", {}))
        return {"unresolved_software_lines_preserved": 12}

    def fake_photos(**kwargs):
        calls.append(("photos", kwargs))
        return {"photo_identifications": 3, "media_assets": 2, "fetch_failures": 0}

    def fake_merge_media():
        calls.append(("merge_media", {}))
        return 2

    def fake_write_audit(photo_results, sinclair_results):
        calls.append(("audit", {"photo": photo_results, "sinclair": sinclair_results}))

    def fake_build_all(**kwargs):
        calls.append(("build_all", kwargs))
        return {"normalise": {"source_items": 15072}, "sqlite_integrity": "ok"}

    monkeypatch.setattr(run_detailed.sinclair_user, "run", fake_sinclair)
    monkeypatch.setattr(run_detailed.stairway, "run", fake_stairway)
    monkeypatch.setattr(run_detailed.sinclair_supplement, "supplement", fake_sinclair_supplement)
    monkeypatch.setattr(run_detailed.stairway_supplement, "supplement", fake_stairway_supplement)
    monkeypatch.setattr(run_detailed.archive_postprocess, "clean_sinclair_supplement", fake_clean)
    monkeypatch.setattr(run_detailed.archive_postprocess, "capture_tynesoft_photo_testimony", fake_photos)
    monkeypatch.setattr(run_detailed.archive_postprocess, "merge_curated_media", fake_merge_media)
    monkeypatch.setattr(run_detailed.archive_postprocess, "write_audit", fake_write_audit)
    monkeypatch.setattr(run_detailed.build_pipeline, "build_all", fake_build_all)

    result = run_detailed.run(
        resume=True,
        include_catalogues=True,
        max_pages=25,
        accessed_at="2026-06-19",
    )

    assert [name for name, _ in calls] == [
        "sinclair",
        "sinclair_supplement",
        "stairway",
        "stairway_supplement",
        "clean_sinclair",
        "photos",
        "build_all",
        "merge_media",
        "audit",
    ]
    assert calls[0][1]["indexes_only"] is False
    assert calls[0][1]["max_pages"] == 25
    assert calls[1][1] == {"accessed_at": "2026-06-19"}
    assert calls[2][1]["include_catalogues"] is True
    assert calls[3][1] == {"accessed_at": "2026-06-19"}
    assert calls[6][1] == {"skip_fetch": True}
    assert result["postprocess"]["photo_identifications"] == 3
    assert result["postprocess"]["media_assets"] == 2
