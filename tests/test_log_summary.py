# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/oidf-log-summary.py using only synthetic logs (examples/sample-logs)."""

import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "oidf-log-summary.py")
SAMPLES = os.path.join(ROOT, "examples", "sample-logs")
EXAMPLES = os.path.join(ROOT, "examples")
COMMON_FAILURES = os.path.join(ROOT, "skills", "oidf-conformance", "references", "common-failures.md")

spec = importlib.util.spec_from_file_location("oidf_log_summary", SCRIPT)
ols = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ols)

# Strings planted in the synthetic logs that must never reach the output.
FORBIDDEN = [
    "SYNTHETIC-PRIVATE-KEY-MUST-NOT-APPEAR",  # testInfo.config private key
    "SECRET-INPUT-MUST-NOT-APPEAR",           # non-allow-listed detail
    "SECRET-SESSION-VALUE",                   # direct_post redirect_uri query
    "eyJ",                                    # JWTs (access token, DPoP proof)
    "000000000000000000000",                  # exporter / owner sub
    "accounts.example.org",                   # exporter / owner iss
    "tester@example.org",                     # e-mail inside a message
    "base64,",                                # uploaded screenshot
]


def run(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = ols.main(list(args))
    return rc, buf.getvalue()


class SummaryTests(unittest.TestCase):

    def test_text_lists_every_module_and_totals(self):
        rc, out = run(SAMPLES)
        self.assertEqual(rc, 0)
        for name in ("oid4vci-1_0-issuer-metadata-test", "fapi2-security-profile-final-happy-flow",
                     "oid4vci-1_0-issuer-batch-issuance", "oid4vp-1final-verifier-happy-flow",
                     "oid4vp-1final-verifier-present-revoked-credential"):
            self.assertIn(name, out)
        self.assertIn("7 test(s): FAILED=4, REVIEW=1, SKIPPED=1, PASSED=1", out)

    def test_condition_classes_and_details(self):
        _rc, out = run(SAMPLES)
        self.assertIn("CheckDiscEndpointClientAttestationSigningAlgValuesSupported (OAuth2-ATCA07-10.1)", out)
        self.assertIn("$.credential_configurations_supported.example_pid.credential_metadata.display[0].lang", out)
        self.assertIn("cipher_suite=TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA", out)
        self.assertIn("unknown_params=purpose", out)
        self.assertIn("response=keys: extra_url, redirect_uri", out)
        self.assertIn("error=invalid_token", out)
        self.assertIn("img=<screenshot uploaded>", out)
        self.assertIn("see references/common-failures.md#cf-tls12-ciphers", out)

    def test_no_secrets_or_account_data_in_any_format(self):
        for fmt in ("text", "markdown", "json"):
            _rc, out = run(SAMPLES, "--format", fmt)
            for bad in FORBIDDEN:
                self.assertNotIn(bad, out, f"{bad!r} leaked in {fmt} output")
            self.assertNotIn('"config"', out)
            self.assertNotIn("testOwner", out)
            self.assertNotIn("exportedBy", out)

    def test_redact_hides_hosts_and_alias_but_keeps_suite_host(self):
        doc = {"testInfo": {"testName": "t", "alias": "my-alias", "result": "FAILED"},
               "results": [{"src": "X", "result": "FAILURE",
                            "msg": "GET https://svc.internal.example/test/a/my-alias/cb and https://demo.certification.openid.net/test/a/my-alias/x"}]}
        row = ols.summarize_doc("x.json", doc, redact_hosts=True)
        msg = row["findings"][0]["message"]
        self.assertNotIn("svc.internal.example", msg)
        self.assertNotIn("my-alias", msg)
        self.assertIn("demo.certification.openid.net", msg)
        self.assertIn("<alias>", msg)

    def test_reads_zip_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            zpath = os.path.join(tmp, "plan-export.zip")
            with zipfile.ZipFile(zpath, "w") as zf:
                for fn in sorted(os.listdir(SAMPLES)):
                    zf.write(os.path.join(SAMPLES, fn), arcname="nested/dir/" + fn)
                zf.writestr("nested/dir/test-log-x.sig", "not json")
                zf.writestr("nested/dir/other.json", json.dumps({"hello": "world"}))
            rows = ols.build_rows([zpath])
            self.assertEqual(len(rows), 7)

    def test_long_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = tmp
            while len(deep) < 320:
                deep = os.path.join(deep, "a-rather-long-directory-name-for-path-testing")
            os.makedirs(ols.long_path(deep))
            src = os.path.join(SAMPLES, "test-log-synthBatch0001.json")
            dst = os.path.join(deep, "test-log-synthBatch0001.json")
            with open(src, "rb") as fh, open(ols.long_path(dst), "wb") as out:
                out.write(fh.read())
            rows = ols.build_rows([tmp])
            self.assertEqual([r["test"] for r in rows], ["oid4vci-1_0-issuer-batch-issuance"])
            shutil.rmtree(ols.long_path(tmp), ignore_errors=True)

    def test_latest_keeps_most_recent_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(SAMPLES, "test-log-synthBatch0001.json"), encoding="utf-8") as fh:
                old = json.load(fh)
            new = json.loads(json.dumps(old))
            new["testInfo"]["started"] = "2026-10-28T09:00:00Z"
            new["testInfo"]["result"] = "PASSED"
            new["results"] = [{"src": "VCIEnsureBatchTimeClaimsNotLinkable", "result": "SUCCESS", "msg": "ok"}]
            for name, d in (("test-log-a.json", old), ("test-log-b.json", new)):
                with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                    json.dump(d, fh)
            self.assertEqual(len(ols.build_rows([tmp])), 2)
            rows = ols.build_rows([tmp], latest=True)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["result"], "PASSED")

    def test_fail_on_exit_codes(self):
        rc, _ = run(SAMPLES, "--fail-on", "FAILED")
        self.assertEqual(rc, 1)
        rc, _ = run(os.path.join(SAMPLES, "test-log-synthVpNeg0001.json"), "--fail-on", "WARNING")
        self.assertEqual(rc, 0)
        with tempfile.TemporaryDirectory() as tmp:
            rc, _ = run(tmp)
            self.assertEqual(rc, 2)

    def test_examples_are_current(self):
        for fmt, fn in (("text", "sample-summary.txt"), ("markdown", "sample-summary.md"), ("json", "sample-summary.json")):
            _rc, out = run(SAMPLES, "--format", fmt)
            with open(os.path.join(EXAMPLES, fn), encoding="utf-8") as fh:
                self.assertEqual(out, fh.read(), f"examples/{fn} is stale; regenerate it")

    def test_hint_anchors_exist(self):
        with open(COMMON_FAILURES, encoding="utf-8") as fh:
            ids = set(re.findall(r'<a id="([a-z0-9-]+)"></a>', fh.read()))
        for anchor in list(ols.HINTS.values()) + list(ols.TEST_HINTS.values()):
            self.assertIn(anchor, ids, f"anchor {anchor} missing in common-failures.md")


if __name__ == "__main__":
    unittest.main()
