"""The tests of link-checker, written BEFORE the code (see SPEC.md). They fail until the package exists.
Every tree here is made up in a temporary folder. No network is used."""
import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linkcheck import anchors, check_tree, extract_links

ROOT = Path(__file__).resolve().parent.parent


def tree(files):
    d = tempfile.TemporaryDirectory()
    for name, text in files.items():
        p = Path(d.name) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return d


def kinds(problems):
    return [(p.path, p.line, p.kind, p.target) for p in problems]


class ExtractTests(unittest.TestCase):
    def test_links_and_images_are_found_with_their_line_numbers(self):
        links = extract_links("# T\n\nSee [a](a.md) and ![pic](img/p.png).\n[b](b.md#x)\n")
        self.assertEqual([(l.line, l.target, l.is_image) for l in links], [(3, "a.md", False), (3, "img/p.png", True), (4, "b.md#x", False)])

    def test_links_in_code_are_skipped(self):
        text = "```\n[no](missing.md)\n```\n~~~\n[no](missing2.md)\n~~~\nSome `[no](missing3.md)` code and [yes](real.md).\n"
        self.assertEqual([l.target for l in extract_links(text)], ["real.md"])

    def test_the_anchors_are_the_github_kind_with_duplicates_numbered(self):
        text = "# Hello, World!\n## Second part\n## Second part\n### Second part\n# C++ and C#\n"
        self.assertEqual(anchors(text), {"hello-world", "second-part", "second-part-1", "second-part-2", "c-and-c"})


class CheckTests(unittest.TestCase):
    def test_a_good_tree_has_no_problem(self):
        with tree({"a.md": "[b](b.md) ![p](img/p.png) [h](b.md#top)\n", "b.md": "# Top\n", "img/p.png": "x"}) as d:
            self.assertEqual(check_tree(d), [])

    def test_a_missing_file_and_a_missing_illustration_are_different_kinds(self):
        with tree({"a.md": "[gone](gone.md)\n![pic](img/gone.png)\n"}) as d:
            self.assertEqual(kinds(check_tree(d)), [("a.md", 1, "broken link", "gone.md"), ("a.md", 2, "missing illustration", "img/gone.png")])

    def test_a_missing_anchor_in_the_same_file_and_in_another(self):
        with tree({"a.md": "# Real\n[x](#real) [y](#nope) [z](b.md#absent)\n", "b.md": "# Present\n"}) as d:
            self.assertEqual(kinds(check_tree(d)), [("a.md", 2, "missing anchor", "#nope"), ("a.md", 2, "missing anchor", "b.md#absent")])

    def test_links_are_relative_to_the_file_that_holds_them(self):
        with tree({"docs/a.md": "[up](../top.md) [sib](b.md) [bad](top.md)\n", "docs/b.md": "x\n", "top.md": "x\n"}) as d:
            self.assertEqual(kinds(check_tree(d)), [("docs/a.md", 1, "broken link", "top.md")])

    def test_query_and_percent_encoding_are_handled(self):
        with tree({"a.md": "[q](b.md?x=1) [p](my%20file.md)\n", "b.md": "x\n", "my file.md": "x\n"}) as d:
            self.assertEqual(check_tree(d), [])

    def test_external_links_are_not_checked(self):
        with tree({"a.md": "[w](https://example.invalid/x) [m](mailto:a@b.invalid) [t](tel:+000) [o](ftp://example.invalid/f)\n"}) as d:
            self.assertEqual(check_tree(d), [])

    def test_a_target_outside_the_root_is_a_problem_and_is_never_opened(self):
        with tree({"sub/a.md": "[out](../../outside.md)\n"}) as d:
            outside = Path(d).parent / "outside.md"
            existed = outside.exists()
            self.assertEqual(kinds(check_tree(d)), [("sub/a.md", 1, "outside the folder", "../../outside.md")])
            self.assertEqual(outside.exists(), existed)

    def test_an_empty_target_is_a_problem(self):
        with tree({"a.md": "[x]()\n"}) as d:
            self.assertEqual(kinds(check_tree(d)), [("a.md", 1, "empty link", "")])

    def test_only_the_given_paths_are_read_and_problems_are_sorted(self):
        files = {"in/z.md": "[x](nope.md)\n", "in/a.md": "[x](nope.md)\n", "out/b.md": "[x](nope.md)\n"}
        with tree(files) as d:
            self.assertEqual([p.path for p in check_tree(d, ["in"])], ["in/a.md", "in/z.md"])
            self.assertEqual(len(check_tree(d)), 3)


class CommandTests(unittest.TestCase):
    def run_cli(self, files, *args):
        with tree(files) as d:
            p = subprocess.run([sys.executable, "-m", "linkcheck", d, *args], cwd=ROOT, capture_output=True, text=True, timeout=60)
            before = sorted(str(x.relative_to(d)) for x in Path(d).rglob("*"))
            return p.returncode, p.stdout, p.stderr, before, sorted(files)

    def test_a_problem_is_one_line_and_exit_1(self):
        rc, out, err, _, _ = self.run_cli({"a.md": "x\n[gone](gone.md)\n"})
        self.assertEqual((rc, out, err), (1, "a.md:2: broken link: gone.md\n1 problem(s).\n", ""))

    def test_no_problem_prints_the_fixed_line_and_exit_0(self):
        rc, out, _, _, _ = self.run_cli({"a.md": "[b](b.md)\n", "b.md": "x\n"})
        self.assertEqual((rc, out), (0, "No problems.\n"))

    def test_a_bad_root_is_one_error_line_and_exit_2_with_no_traceback(self):
        p = subprocess.run([sys.executable, "-m", "linkcheck", "/nonexistent-folder-for-the-test"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 2)
        self.assertTrue(p.stderr.startswith("error: ") and p.stderr.count("\n") == 1 and "Traceback" not in p.stderr, p.stderr)

    def test_nothing_is_written_to_the_checked_folder(self):
        rc, _, _, before, files = self.run_cli({"a.md": "[gone](gone.md)\n"})
        self.assertEqual(before, files)


class RulesOfTheRepoTests(unittest.TestCase):
    def test_no_module_of_the_package_opens_a_connection(self):
        banned = {"socket", "urllib", "http", "requests", "ssl", "ftplib", "smtplib", "telnetlib", "xmlrpc"}
        pkg = ROOT / "linkcheck"
        self.assertTrue(pkg.is_dir())
        for path in pkg.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else \
                        [(node.module or "").split(".")[0]] if isinstance(node, ast.ImportFrom) else []
                self.assertFalse(banned & set(names), f"{path.name} imports {banned & set(names)}")


if __name__ == "__main__":
    unittest.main()
