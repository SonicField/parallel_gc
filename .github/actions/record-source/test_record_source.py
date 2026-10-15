"""Exercise the source-record shell script against temporary Git repositories."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-c", "user.name=CI fixture",
         "-c", "user.email=ci-fixture@example.invalid", *args],
        cwd=repo, text=True, stderr=subprocess.PIPE,
    ).strip()


class SourceRecordTests(unittest.TestCase):
    def check_record(self, case):
        action = Path(__file__).with_name("action.yml").read_text()
        match = re.search(r"      run: \|\n((?:        .*\n|\n)+)", action)
        self.assertIsNotNone(match)
        script = textwrap.dedent(match.group(1))

        with tempfile.TemporaryDirectory(prefix="parallel-gc-ci-source-") as tmp:
            repo = Path(tmp)
            cp = repo / "cpython"
            cp.mkdir()
            git(cp, "init", "-q")
            (cp / "fixture.txt").write_text("clean\n")
            git(cp, "add", "fixture.txt")
            git(cp, "commit", "-qm", "fixture baseline")
            cp_sha = git(cp, "rev-parse", "HEAD")
            git(repo, "init", "-q")
            git(repo, "update-index", "--add", "--cacheinfo",
                f"160000,{cp_sha},cpython")
            git(repo, "commit", "-qm", "pin fixture")
            parent = git(repo, "rev-parse", "HEAD")
            env = dict(
                os.environ, GITHUB_SHA=parent, RUNNER_OS="Linux",
                RUNNER_ARCH="ARM64", CI_BUILD_FLAGS="--with-parallel-gc",
                GITHUB_REPOSITORY="fixture/parallel_gc", GITHUB_RUN_ID="1",
                GITHUB_RUN_ATTEMPT="2",
            )
            if case == "workflow_sha":
                env["GITHUB_SHA"] = "0" * 40
            elif case == "cpython_checkout":
                git(cp, "commit", "--allow-empty", "-qm", "unpinned fixture")
            elif case == "dirty_source":
                (cp / "fixture.txt").write_text("changed\n")

            result = subprocess.run(
                ["bash", "-c", script], cwd=repo, env=env,
                text=True, capture_output=True,
            )
            if case == "matching":
                self.assertEqual(result.returncode, 0, result.stderr)
            else:
                self.assertNotEqual(result.returncode, 0, result.stdout)
            record = (repo / "ci-source.txt").read_text()
            self.assertIn(f"parent_revision={parent}\n", record)
            self.assertIn(f"cpython_gitlink={cp_sha}\n", record)
            self.assertIn("run_attempt=2\n", record)

    def test_matching_checkout(self):
        self.check_record("matching")

    def test_wrong_workflow_sha(self):
        self.check_record("workflow_sha")

    def test_wrong_cpython_checkout(self):
        self.check_record("cpython_checkout")

    def test_dirty_cpython_source(self):
        self.check_record("dirty_source")


if __name__ == "__main__":
    unittest.main()
