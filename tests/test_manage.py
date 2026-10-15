import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("manage", Path(__file__).parents[1] / "scripts/manage.py")
manage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repository"
        self.home = Path(self.temp.name) / "home"
        (self.root / "skills/example").mkdir(parents=True)
        (self.root / "skills/example/SKILL.md").write_text("---\nname: example\ndescription: A useful example.\n---\nbody\n")
        (self.root / "profiles").mkdir()
        (self.root / "profiles/common.md").write_text("Common profile\n")
        (self.root / "profiles/codex.md").write_text("Codex supplement\n")
        self.data = {"schema": 1, "skills": [{"name": "example", "source": "skills/example", "platforms": ["codex", "claude"]}], "retired": {"old-skill": "example"}}
        self.save()

    def save(self):
        (self.root / "manifest.json").write_text(json.dumps(self.data))

    def test_same_source_two_hosts_and_idempotence(self):
        self.assertTrue(manage.install(self.root, self.home, "apply")["changes"])
        self.assertEqual((self.home / ".agents/skills/example").resolve(), (self.home / ".claude/skills/example").resolve())
        self.assertIn("Codex supplement", (self.home / ".codex/AGENTS.md").read_text())
        self.assertNotIn("Codex supplement", (self.home / ".claude/CLAUDE.md").read_text())
        self.assertTrue(manage.install(self.root, self.home, "apply")["clean"])

    def test_dry_run_has_no_writes(self):
        manage.install(self.root, self.home, "dry-run")
        self.assertFalse(self.home.exists())
        self.assertFalse((self.root / ".local").exists())

    def test_conflict_before_any_writes(self):
        conflict = self.home / ".claude/skills/example"
        conflict.mkdir(parents=True)
        marker = conflict / "keep.txt"
        marker.write_text("personal changes")
        with self.assertRaises(manage.Conflict):
            manage.install(self.root, self.home, "apply")
        self.assertEqual(marker.read_text(), "personal changes")
        self.assertFalse((self.home / ".agents").exists())
        self.assertFalse((self.root / ".local").exists())

    def test_retired_source_cannot_return(self):
        self.data["retired"]["example"] = "retired"
        self.save()
        with self.assertRaises(manage.Conflict):
            manage.install(self.root, self.home, "apply")

    def test_retired_unmanaged_directory_preserved(self):
        old = self.home / ".claude/skills/old-skill"
        old.mkdir(parents=True)
        with self.assertRaises(manage.Conflict):
            manage.install(self.root, self.home, "apply")
        self.assertTrue(old.is_dir())

    def test_retired_owned_link_removed_only(self):
        old = self.home / ".claude/skills/old-skill"
        old.parent.mkdir(parents=True)
        old.symlink_to(self.root / "skills/old-skill")
        unrelated = old.parent / "unrelated.txt"
        unrelated.write_text("keep")
        manage.install(self.root, self.home, "apply")
        self.assertFalse(old.is_symlink())
        self.assertEqual(unrelated.read_text(), "keep")

    def test_source_escape_rejected(self):
        self.data["skills"][0]["source"] = "../outside"
        self.save()
        with self.assertRaises(manage.Conflict):
            manage.install(self.root, self.home, "apply")

    def test_destination_parent_escape_rejected(self):
        external = Path(self.temp.name) / "outside"
        external.mkdir()
        self.home.mkdir()
        (self.home / ".claude").symlink_to(external)
        with self.assertRaises(manage.Conflict):
            manage.install(self.root, self.home, "apply")
        self.assertEqual(list(external.iterdir()), [])

    def test_optional_local_skill_missing_reported(self):
        self.data["local_skills"] = [{"name": "private-skill", "source": ".local/skills/private-skill", "platforms": ["codex", "claude"]}]
        self.save()
        self.assertEqual(len(manage.install(self.root, self.home, "apply")["notices"]), 1)


if __name__ == "__main__":
    unittest.main()
