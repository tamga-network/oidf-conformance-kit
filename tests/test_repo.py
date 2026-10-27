# SPDX-License-Identifier: Apache-2.0
"""Repository checks: manifests, frontmatter, and that every relative Markdown link (and anchor) resolves."""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def md_files():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".md"):
                yield os.path.join(dirpath, fn)


def github_slug(heading):
    s = heading.strip().lower()
    s = re.sub(r"[`*_~]", "", s)
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors_of(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text_wo_code = re.sub(r"```.*?```", "", text, flags=re.S)
    ids = set(re.findall(r'<a id="([^"]+)"></a>', text_wo_code))
    seen = {}
    for line in text_wo_code.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            slug = github_slug(m.group(1))
            n = seen.get(slug, 0)
            ids.add(slug if n == 0 else f"{slug}-{n}")
            seen[slug] = n + 1
    return ids


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class RepoTests(unittest.TestCase):

    def test_plugin_manifest(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertRegex(m["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertFalse(m["name"].startswith(("claude-", "anthropic-")))
        for key in ("version", "description", "author", "license"):
            self.assertIn(key, m)
        self.assertEqual(m["license"], "Apache-2.0")

    def test_marketplace_manifest(self):
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
            mk = json.load(fh)
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            name = json.load(fh)["name"]
        self.assertIn("name", mk)
        self.assertIn("name", mk["owner"])
        entry = [p for p in mk["plugins"] if p["name"] == name]
        self.assertEqual(len(entry), 1, "marketplace entry name must equal plugin.json name")
        self.assertTrue(os.path.isdir(os.path.join(ROOT, entry[0]["source"])))
        self.assertNotIn("..", entry[0]["source"])

    def test_skill_and_agent_frontmatter(self):
        skills_dir = os.path.join(ROOT, "skills")
        for name in os.listdir(skills_dir):
            fm = frontmatter(os.path.join(skills_dir, name, "SKILL.md"))
            self.assertIsNotNone(fm, name)
            self.assertEqual(fm.get("name"), name)
            self.assertGreater(len(fm.get("description", "")), 40)
        agents_dir = os.path.join(ROOT, "agents")
        for fn in os.listdir(agents_dir):
            fm = frontmatter(os.path.join(agents_dir, fn))
            self.assertIsNotNone(fm, fn)
            self.assertEqual(fm.get("name"), fn[:-3])
            self.assertIn("description", fm)
            self.assertEqual({t.strip() for t in fm["tools"].split(",")}, {"Read", "Grep", "Glob", "Bash", "Edit", "Write"})

    def test_config_templates_are_json(self):
        d = os.path.join(ROOT, "skills", "oidf-conformance", "references", "config-templates")
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn), encoding="utf-8") as fh:
                    cfg = json.load(fh)
                self.assertIn("alias", cfg)
                self.assertIn("REPLACE", json.dumps(cfg), f"{fn} must stay a template")

    def test_markdown_links_resolve(self):
        problems = []
        for path in md_files():
            with open(path, encoding="utf-8") as fh:
                text = re.sub(r"```.*?```", "", fh.read(), flags=re.S)
            for target in LINK_RE.findall(text):
                if re.match(r"^[a-z]+:", target) or target.startswith("${"):
                    continue
                file_part, _, anchor = target.partition("#")
                dest = os.path.normpath(os.path.join(os.path.dirname(path), file_part)) if file_part else path
                if not os.path.exists(dest):
                    problems.append(f"{os.path.relpath(path, ROOT)}: missing {target}")
                    continue
                if anchor and dest.endswith(".md") and anchor not in anchors_of(dest):
                    problems.append(f"{os.path.relpath(path, ROOT)}: missing anchor {target}")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
