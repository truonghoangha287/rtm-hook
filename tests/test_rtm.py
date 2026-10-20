import json
import tempfile
import unittest
from pathlib import Path

from fixture import cli, edit, hook, make

from rtmlib import core
from rtmlib.config import load
from rtmlib.graph import Graph
from rtmlib.ids import IdSyntax


class IdsTest(unittest.TestCase):
    def setUp(self):
        self.s = IdSyntax(["FR", "NFR", "ADR", "SD", "STORY", "TASK"], {"STORY": "AC"})

    def keys(self, text):
        return [h.key for h in self.s.find(text)]

    def test_slash_list(self):
        self.assertEqual(self.keys("FR-009/010"), ["FR-9", "FR-10"])

    def test_dot_range(self):
        self.assertEqual(self.keys("FR-001..003"), ["FR-1", "FR-2", "FR-3"])
        self.assertEqual(self.keys("FR-001..FR-002"), ["FR-1", "FR-2"])

    def test_dash_range_needs_equal_width(self):
        self.assertEqual(self.keys("FR-009-011"), ["FR-9", "FR-10", "FR-11"])
        self.assertEqual(self.keys("FR-009-1"), ["FR-9"])

    def test_padding_and_prefix_boundaries(self):
        self.assertEqual(self.keys("ADR-5 and ADR-05"), ["ADR-5", "ADR-5"])
        self.assertEqual(self.keys("NFR-001 DSD-01 BRule-1"), ["NFR-1"])

    def test_composite(self):
        self.assertIn("STORY-1/AC4", self.keys("Verifies: STORY-001/AC4"))
        self.assertIn("STORY-1/AC5", self.keys("see STORY-001 AC5"))

    def test_marker_suffix(self):
        self.assertEqual(self.s.first("TASK-014 ⟐"), ("TASK", "014"))
        self.assertEqual(self.s.first("**TASK-014**"), ("TASK", "014"))


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make(Path(self.tmp.name))
        self.cfg = load(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chain(self):
        g = Graph.build(self.cfg)
        d = g.descendants("BR-1")
        self.assertEqual(d["req"], ["FR-1"])
        self.assertEqual(d["lld"], ["TASK-1"])
        self.assertEqual(d["code"], ["src/main/Gateway.java"])
        self.assertEqual(d["test"], ["src/test/GatewayTest.java"])
        self.assertEqual(g.source(g.nodes["TASK-1"]), "Regulation X")
        self.assertEqual(g.ancestors("src/test/GatewayTest.java")["br"], ["BR-1"])

    def test_lld_traces_via_req_not_hld(self):
        # TASK-001 cites CMP-001 too, but downstream of BR-002 must not include it
        g = Graph.build(self.cfg)
        self.assertEqual(g.descendants("BR-2")["lld"], ["TASK-2"])

    def test_clean_fixture_has_only_expected_findings(self):
        res = core.check(self.cfg)
        self.assertEqual([(f.rule, f.subject) for f in res.findings],
                         [("NOT-COVERED", "BR-2")])

    def test_dangling(self):
        edit(self.root, "src/test/GatewayTest.java", "STORY-001/AC1", "STORY-001/AC9")
        res = core.check(self.cfg)
        p0 = [f for f in res.findings if f.severity == "P0"]
        self.assertEqual(len(p0), 1)
        self.assertIn("STORY-001/AC9", p0[0].msg)

    def test_lld_needs_both(self):
        edit(self.root, "docs/lld.md", "FR-002 · CMP-002", "FR-002")
        res = core.check(self.cfg)
        f = [f for f in res.findings if f.rule == "MISSING-UPSTREAM"]
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0].subject, f[0].severity), ("TASK-2", "P1"))
        self.assertIn("HLD", f[0].msg)

    def test_test_without_verifies(self):
        edit(self.root, "src/test/GatewayTest.java", "Verifies:", "Mentions")
        res = core.check(self.cfg)
        self.assertTrue(any(f.rule == "MISSING-UPSTREAM" and "Verifies:" in f.msg
                            for f in res.findings))


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make(Path(self.tmp.name))
        self.cfg = load(self.root)
        self.rtm = self.root / "docs/rtm.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_sync_is_idempotent_and_keeps_hand_sections(self):
        core.sync(self.cfg)
        first = self.rtm.read_text()
        res, _ = core.sync(self.cfg)
        self.assertEqual(first, self.rtm.read_text())
        self.assertEqual(res.changes, {})
        self.assertIn("Hand-written notes stay put.", first)
        self.assertIn("| BR-001 | Regulation X | FR-001 | CMP-001 | TASK-001 | Gateway | GatewayTest | Tested |",
                      first)
        self.assertIn("| BR-002 | Regulation Y | FR-002 | CMP-002 | TASK-002 | Screener | — | Implemented |",
                      first)
        self.assertIn("| STORY-001 | FR-001 | 1/2 | AC2 | GatewayTest |", first)

    def test_source_is_not_read_from_generated_blocks(self):
        core.sync(self.cfg)
        # removing the hand Source row must not be masked by the generated forward table
        self.rtm.write_text(self.rtm.read_text().replace("| BR-001 | Regulation X | MUST |\n", ""))
        res = core.check(self.cfg)
        self.assertTrue(any(f.subject == "BR-1" and f.rule == "MISSING-UPSTREAM" for f in res.findings))

    def test_gen_edited_detected_and_overwritten(self):
        core.sync(self.cfg)
        self.rtm.write_text(self.rtm.read_text().replace("| TASK-001 |", "| TASK-001 (hand) |", 1))
        self.assertTrue(any(f.rule == "GEN-EDITED" for f in core.check(self.cfg).findings))
        res, _ = core.sync(self.cfg)
        self.assertTrue(res.discarded)
        self.assertFalse(any(f.rule == "GEN-EDITED" for f in core.check(self.cfg).findings))

    def test_cli(self):
        r = cli(self.root, "sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = cli(self.root, "check", "--gate")
        self.assertEqual(r.returncode, 0, r.stdout)
        edit(self.root, "src/test/GatewayTest.java", "AC1", "AC9")
        self.assertEqual(cli(self.root, "check", "--gate").returncode, 1)
        out = json.loads(cli(self.root, "check", "--json").stdout)
        self.assertFalse(out["pass"])
        self.assertEqual(out["counts"]["P0"], 1)
        self.assertIn("BR-001", cli(self.root, "why", "TASK-001").stdout)


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make(Path(self.tmp.name))
        self.assertEqual(cli(self.root, "sync").returncode, 0)
        self.assertEqual(cli(self.root, "baseline").returncode, 0)
        self.rtm = self.root / "docs/rtm.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_unrelated_file_is_silent(self):
        (self.root / "README.md").write_text("x")
        out = hook(self.root, "post", {"tool_name": "Write",
                                       "tool_input": {"file_path": str(self.root / "README.md")}})
        self.assertIsNone(out)
        self.assertFalse((self.root / ".rtm/dirty").exists())

    def test_pre_denies_edit_inside_generated_block(self):
        out = hook(self.root, "pre", {"tool_name": "Edit", "tool_input": {
            "file_path": str(self.rtm), "old_string": "| TASK-001 |", "new_string": "| TASK-009 |"}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_pre_allows_hand_section_edit(self):
        out = hook(self.root, "pre", {"tool_name": "Edit", "tool_input": {
            "file_path": str(self.rtm), "old_string": "Hand-written notes", "new_string": "Notes"}})
        self.assertIsNone(out)

    def test_pre_denies_write_that_changes_a_block(self):
        content = self.rtm.read_text().replace("| TASK-001 |", "| TASK-009 |")
        out = hook(self.root, "pre", {"tool_name": "Write",
                                      "tool_input": {"file_path": str(self.rtm), "content": content}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_post_doc_edit_syncs_and_reports(self):
        p = edit(self.root, "docs/lld.md", "| TASK-002 ⟐ |",
                 "| TASK-003 | Build audit | FR-001 |\n| TASK-002 ⟐ |")
        out = hook(self.root, "post", p)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("RTM synced", ctx)
        self.assertIn("TASK-003 has no HLD reference", ctx)
        self.assertIn("| TASK-003 | — | FR-001 | ✗ |", self.rtm.read_text())

    def test_post_code_edit_is_silent_and_marks_dirty(self):
        p = edit(self.root, "src/test/GatewayTest.java", "AC1", "AC9")
        self.assertIsNone(hook(self.root, "post", p))
        self.assertIn("src/test/GatewayTest.java", (self.root / ".rtm/dirty").read_text())

    def test_stop_blocks_on_new_p0_then_allows_after_fix(self):
        p = edit(self.root, "src/test/GatewayTest.java", "AC1", "AC9")
        hook(self.root, "post", p)
        out = hook(self.root, "stop", {"stop_hook_active": False})
        self.assertEqual(out["decision"], "block")
        self.assertIn("STORY-001/AC9", out["reason"])
        # Claude fixes it
        p = edit(self.root, "src/test/GatewayTest.java", "AC9", "AC2")
        hook(self.root, "post", p)
        out = hook(self.root, "stop", {"stop_hook_active": True})
        self.assertNotEqual((out or {}).get("decision"), "block")
        self.assertFalse((self.root / ".rtm/dirty").exists())
        self.assertIn("| STORY-001 | FR-001 | 1/2 | AC1 | GatewayTest |", self.rtm.read_text())

    def test_stop_hook_active_never_loops(self):
        hook(self.root, "post", edit(self.root, "src/test/GatewayTest.java", "AC1", "AC9"))
        out = hook(self.root, "stop", {"stop_hook_active": True})
        self.assertNotEqual((out or {}).get("decision"), "block")
        self.assertIn("left open", out["systemMessage"])

    def test_stop_ignores_baselined_debt(self):
        # pre-existing NOT-COVERED BR-002 is baselined; a clean code edit must not block
        hook(self.root, "post", edit(self.root, "src/main/Gateway.java", "Gateway (", "Gateway API ("))
        out = hook(self.root, "stop", {"stop_hook_active": False})
        self.assertNotEqual((out or {}).get("decision"), "block")

    def test_no_config_is_noop(self):
        (self.root / "rtm.config.json").unlink()
        self.assertIsNone(hook(self.root, "stop", {}))


if __name__ == "__main__":
    unittest.main()
