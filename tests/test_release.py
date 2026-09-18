import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from scripts import transitops


ROOT = Path(__file__).parents[1]
DBT = ROOT / ".venv" / "bin" / "dbt"


class ReleasePublicationTest(unittest.TestCase):
    def test_release_paths_reject_symlinks_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            releases.mkdir()
            manifest = root / "current.json"
            manifest.write_text('{"release": "old.duckdb"}\n')
            linked_releases = root / "linked-releases"
            linked_releases.symlink_to(releases, target_is_directory=True)

            with self.assertRaises(ValueError):
                transitops.build_and_publish_release(
                    linked_releases, manifest, project_dir=root, dbt_bin=DBT
                )
            linked_manifest = root / "linked.json"
            linked_manifest.symlink_to(manifest)
            with self.assertRaises(ValueError):
                transitops.publish_manifest(linked_manifest, {"path": "new.duckdb"})

    def test_release_subprocess_timeout_is_bounded_and_preserves_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            releases.mkdir()
            manifest = root / "current.json"
            manifest.write_text('{"release": "old.duckdb"}\n')
            fake_dbt = root / "dbt"
            fake_dbt.write_text("#!/bin/sh\nsleep 2\n")
            fake_dbt.chmod(0o700)

            with self.assertRaises(transitops.ReleaseBuildError):
                transitops.build_and_publish_release(
                    releases,
                    manifest,
                    project_dir=root,
                    dbt_bin=fake_dbt,
                    _timeout=0.01,
                )
            self.assertEqual(manifest.read_text(), '{"release": "old.duckdb"}\n')
            self.assertEqual(list(releases.iterdir()), [])

    def test_static_activation_failure_keeps_previous_version_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            state = root / "state"
            data.mkdir()
            state.mkdir()
            old_digest = "a" * 64
            namespace = state / "static" / "production"
            namespace.mkdir(parents=True)
            old_metadata = {"sha256": old_digest, "activated_at": "old"}
            (namespace / "active.json").write_text(json.dumps(old_metadata))
            active = data / "static" / "active"
            active.mkdir(parents=True)
            (active / f"{old_digest}.zip").write_bytes(b"old")

            original = transitops.guarded_atomic_write

            def fail_metadata(root_path, relative, chunks, **kwargs):
                if Path(relative) == Path("active.json"):
                    raise OSError("metadata write failed")
                return original(root_path, relative, chunks, **kwargs)

            with patch.object(transitops, "guarded_atomic_write", fail_metadata):
                with self.assertRaises(OSError):
                    transitops._activate_static_transaction(
                        data,
                        state,
                        "production",
                        "b" * 64,
                        b"new",
                        {"sha256": "b" * 64},
                    )
            self.assertEqual(json.loads((namespace / "active.json").read_text()), old_metadata)
            self.assertEqual((active / f"{old_digest}.zip").read_bytes(), b"old")

    def test_retention_keeps_current_and_previous_verified_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            releases.mkdir()
            release_paths = [releases / f"release-{name}" for name in ("old", "previous", "current")]
            for path in release_paths:
                path.mkdir()
                (path / "transitops.duckdb").write_bytes(b"verified")
            manifest = root / "current.json"
            manifest.write_text(json.dumps({"path": str(release_paths[-1] / "transitops.duckdb"), "verified_read_only": True}))

            result = transitops.retain_releases(releases, manifest)

            self.assertEqual(result["removed"], 1)
            self.assertFalse(release_paths[0].exists())
            self.assertTrue(release_paths[1].exists())
            self.assertTrue(release_paths[2].exists())

    def test_retention_keeps_release_referenced_by_active_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            releases.mkdir()
            paths = [releases / f"release-{name}" for name in ("reader", "previous", "current")]
            for path in paths:
                path.mkdir()
                (path / "transitops.duckdb").write_bytes(b"verified")
            manifest = root / "current.json"
            manifest.write_text(json.dumps({"path": str(paths[-1] / "transitops.duckdb"), "verified_read_only": True}))
            readers = root / "readers"
            readers.mkdir()
            (readers / "reader-1").write_text(str(paths[0] / "transitops.duckdb"))

            transitops.retain_releases(releases, manifest, active_readers_root=readers)

            self.assertTrue(paths[0].exists())

    def test_retention_removes_only_unreferenced_older_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            releases.mkdir()
            keep = releases / "release-keep"
            previous = releases / "release-z-previous"
            remove = releases / "release-a-remove"
            candidate = releases / ".candidate-failed"
            for path in (keep, remove, previous, candidate):
                path.mkdir()
                (path / "transitops.duckdb").write_bytes(b"x")
            manifest = root / "current.json"
            manifest.write_text(json.dumps({"path": str(keep / "transitops.duckdb"), "verified_read_only": True}))

            transitops.retain_releases(releases, manifest)

            self.assertFalse(remove.exists())
            self.assertTrue(candidate.exists())

    def test_manifest_replacement_is_atomic_and_failed_candidate_keeps_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "current.json"
            manifest.write_text('{"path": "healthy.duckdb"}\n')
            transitops.publish_manifest(manifest, {"path": "new.duckdb", "verified_read_only": True})
            self.assertEqual(json.loads(manifest.read_text())["path"], "new.duckdb")
            self.assertFalse((root / ".current.json.tmp").exists())

    def test_failed_build_preserves_current_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            releases = Path(directory) / "releases"
            releases.mkdir()
            manifest = Path(directory) / "current.json"
            manifest.write_text('{"release": "old.duckdb"}\n')

            with self.assertRaises(transitops.ReleaseBuildError):
                transitops.build_and_publish_release(
                    releases,
                    manifest,
                    project_dir=ROOT / "missing-dbt-project",
                    dbt_bin=DBT,
                )

            self.assertEqual(manifest.read_text(), '{"release": "old.duckdb"}\n')
            self.assertEqual(list(releases.iterdir()), [])

    def test_successful_build_reopens_read_only_before_manifest_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            manifest = root / "current.json"

            result = transitops.build_and_publish_release(
                releases,
                manifest,
                project_dir=ROOT,
                dbt_bin=DBT,
            )

            published = Path(result["path"])
            self.assertTrue(published.is_file())
            self.assertEqual(json.loads(manifest.read_text())["path"], str(published))
            connection = duckdb.connect(str(published), read_only=True)
            try:
                self.assertEqual(
                    connection.sql("select observation_count from main_marts.mart_reliability").fetchone()[0],
                    3,
                )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
