"""Generated contract suite over every shipped template plus custom flows.

Each flow is turned into synthetic repos by rtmlib.synth; rtmlib.contract runs the same promises
for every step of the flow. A team's own flow is checked the same way with `rtm.py selftest`.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixture import SCRIPTS

from rtmlib import checks, contract, flow
from rtmlib.config import Config, ConfigError

TEMPLATES = SCRIPTS.parent / "templates"

# A flow that is not a template: heading root, `all` rule on a files step, single-file matrix.
CUSTOM = {
    "schema": 2,
    "vars": {"d": "<docs dir, e.g. design>"},
    "rtm": {"index": "{d}/trace.md"},
    "flow": [
        {"step": "goal", "label": "Goal", "produces": {"ids": ["GOAL"], "in": [{"files": ["{d}/goals.md"], "how": "heading"}]}},
        {"step": "sr", "label": "SysReq", "severity": "P1",
         "produces": {"ids": ["SR"], "in": [{"files": ["{d}/sysreq.md"], "how": "table"}]},
         "consumes": {"steps": ["goal"]}},
        {"step": "dd", "label": "Design", "severity": "P2",
         "produces": {"ids": ["DD", "IF"], "in": [{"files": ["{d}/design/*.md"], "how": "table"}]},
         "consumes": {"steps": ["sr"]}},
        {"step": "vt", "label": "Verification", "severity": "P1",
         "produces": {"files": ["verification/**/*.feature"]},
         "consumes": {"steps": ["sr", "dd"], "rule": "all", "marker": "@covers"}},
    ],
    "coverage": [{"from": "sr", "to": "vt"}],
    "views": "auto",
}

# Same flow, split into section files with sharding, and a child step.
CUSTOM_SPLIT = copy.deepcopy(CUSTOM)
CUSTOM_SPLIT["rtm"] = {"index": "{d}/trace.md", "dir": "{d}/trace", "shard_size": 1}
CUSTOM_SPLIT["flow"][1]["produces"]["children"] = {
    "step": "crit", "label": "Criterion", "suffix": "C", "pattern": r"^C(\d+):", "example": "C{n}: holds"}
CUSTOM_SPLIT["flow"][1]["produces"]["in"][0]["how"] = "heading"
CUSTOM_SPLIT["flow"][3]["consumes"] = {"steps": ["crit", "dd"], "rule": "all", "marker": "@covers"}


def flows():
    for d in sorted(TEMPLATES.iterdir()):
        yield f"template:{d.name}", json.loads((d / "flow.json").read_text())
    yield "custom:single-file", CUSTOM
    yield "custom:split+children", CUSTOM_SPLIT


class ContractTest(unittest.TestCase):
    def test_every_flow_meets_every_contract(self):
        for name, raw in flows():
            cases = contract.run(raw)
            self.assertGreater(len(cases), 8, name)
            for c in cases:
                with self.subTest(flow=name, case=c.name):
                    self.assertTrue(c.ok, c.detail)

    def test_suite_covers_each_step_rule(self):
        names = [c.name for c in contract.run(CUSTOM)]
        self.assertIn("[vt] dropping 'sr' raises MISSING-UPSTREAM P1", names)
        self.assertIn("[vt] dropping 'dd' raises MISSING-UPSTREAM P1", names)
        self.assertIn("[dd] an undefined Design ID is reported as DANGLING P0", names)


class SuiteCanFailTest(unittest.TestCase):
    """The generated tests must catch a broken engine or a broken flow, not just pass."""

    def test_detects_disabled_rule(self):
        saved = list(checks._FUNCS)
        checks._FUNCS[:] = [f for f in saved if f.rid != "MISSING-UPSTREAM"]
        try:
            failed = [c.name for c in contract.run(CUSTOM) if not c.ok]
        finally:
            checks._FUNCS[:] = saved
        self.assertTrue(any("MISSING-UPSTREAM" in n for n in failed), failed)

    def test_detects_disabled_dangling(self):
        saved = list(checks._FUNCS)
        checks._FUNCS[:] = [f for f in saved if f.rid != "DANGLING"]
        try:
            failed = [c.name for c in contract.run(CUSTOM) if not c.ok]
        finally:
            checks._FUNCS[:] = saved
        self.assertTrue(any("DANGLING" in n for n in failed), failed)

    def test_invalid_flows_are_rejected(self):
        bad = {
            "unknown step": lambda r: r["flow"][1]["consumes"].update(steps=["nope"]),
            "prefix twice": lambda r: r["flow"][2]["produces"].update(ids=["SR"]),
            "cycle": lambda r: r["flow"][0].update(consumes={"steps": ["sr"]}),
            "walk not subset": lambda r: r["flow"][3]["consumes"].update(walk=["goal"]),
            "example vs pattern": lambda r: r["flow"][1]["produces"].update(children={
                "step": "c", "suffix": "C", "pattern": r"^C(\d+):", "example": "nope"}),
            "unset var": lambda r: r.update(vars={"d": "<docs dir>"}),
        }
        for name, mutate in bad.items():
            raw = copy.deepcopy(CUSTOM)
            if name != "unset var":
                raw["vars"] = {"d": "design"}
            mutate(raw)
            with self.subTest(name):
                with self.assertRaises(ConfigError):
                    Config(Path("."), raw)
                if name != "unset var":  # selftest fills placeholders on purpose; install does not
                    self.assertFalse(contract.run(raw)[0].ok)


class CliFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def rtm(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "rtm.py"), "--root", str(self.root), *args],
                              capture_output=True, text=True)

    def test_templates_init_show_check_selftest(self):
        self.assertIn("esdlc-waterfall", self.rtm("templates").stdout)
        r = self.rtm("init", "--template", "minimal", "--set", "req_file=docs/req.md",
                     "--set", "src=src", "--set", "tests=tests", "--set", "rtm_index=docs/rtm.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.root / "rtm.config.json").exists())
        self.assertTrue((self.root / "docs/rtm.md").exists())
        self.assertIn("matches no files", r.stdout)  # doctor: repo has no artifacts yet
        show = self.rtm("flow", "show").stdout
        self.assertIn("[test] Test", show)
        self.assertIn("must cite req", show)
        self.assertEqual(self.rtm("init", "--template", "minimal").returncode, 2)  # no overwrite
        st = self.rtm("selftest")
        self.assertEqual(st.returncode, 0, st.stdout[-800:])

    def test_init_requires_vars(self):
        r = self.rtm("init", "--template", "agile")
        self.assertEqual(r.returncode, 2)
        self.assertIn("vars not set", r.stderr)


if __name__ == "__main__":
    unittest.main()
