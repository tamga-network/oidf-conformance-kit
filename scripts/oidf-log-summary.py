#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Summarize OpenID Foundation conformance suite test logs.

Reads the JSON logs exported from the conformance suite (plan page "Export", or a single
test's "Download log"), either unpacked into folders or still inside the .zip exports, and
prints one line per test module plus every FAILURE / WARNING / REVIEW entry with its
condition class, requirement codes and the details that matter for triage.

Safe to paste into an issue or a pull request: account data (exportedBy, owner, testOwner),
the test configuration (which holds private keys), tokens, codes, JWTs and uploaded
screenshots are never printed. Details are allow-listed, not block-listed.

Usage:
    python oidf-log-summary.py LOGS... [--format text|markdown|json] [--latest]
                               [--only-problems] [--redact] [--fail-on LEVEL]

LOGS may be files (.json or .zip) or directories (searched recursively).
Standard library only; Python 3.8+. Works with Windows paths longer than 260 characters.
"""

import argparse
import json
import os
import re
import sys
import zipfile

VERSION = "0.1.0"

# Log-entry levels worth showing (SUCCESS and INFO are counted, not listed).
PROBLEM_LEVELS = ("FAILURE", "WARNING", "REVIEW")
NOTE_LEVELS = ("SKIPPED", "INTERRUPTED")

# Detail keys that are safe and useful for triage. Anything else in a log entry is dropped.
SAFE_DETAIL_KEYS = (
    "requirements",
    "expected", "actual", "required",
    "expected_error", "error", "error_description",
    "unknown_properties", "unknown_params", "unexpected",
    "precise_time_claims", "iat_distinct_values", "exp_distinct_values",
    "delta_iat_seconds", "delta_exp_seconds", "delta_response_time_seconds", "tolerance_seconds",
    "cipher_suite", "port", "tls_version",
    "error_class", "cause",
    "image_no_longer_required",
    "content_type", "expected_content_type",
    "missing", "missing_fields", "unsupported",
    "credential_response",
)
# Keys whose value is replaced by a short marker (presence matters, content does not).
MARKER_KEYS = {
    "upload": "<screenshot requested>",
    "img": "<screenshot uploaded>",
    "response": None,  # direct_post response: keys only, see _render_value
    "response_headers": None,  # header names only
}

# Known condition classes -> anchor in skills/oidf-conformance/references/common-failures.md
HINTS = {
    "CheckDiscEndpointClientAttestationSigningAlgValuesSupported": "cf-client-attestation-alg-metadata",
    "CheckForUnexpectedParametersInCredentialIssuerMetadata": "cf-issuer-metadata-unknown-properties",
    "CheckForUnexpectedParametersInServerMetadata": "cf-issuer-metadata-unknown-properties",
    "VCIValidateDisplayLocales": "cf-issuer-metadata-unknown-properties",
    "VCIWarnOnNonCanonicalDisplayLocales": "cf-issuer-metadata-unknown-properties",
    "VCICheckForOldSdJwtFormatInCredentialConfigurations": "cf-issuer-metadata-unknown-properties",
    "VCIValidateNoUnknownKeysInCredentialResponse": "cf-unknown-keys-in-responses",
    "VCIValidateNoUnknownKeysInCredentialErrorResponse": "cf-unknown-keys-in-responses",
    "ValidateDirectPostResponse": "cf-unknown-keys-in-responses",
    "CheckForUnexpectedParametersInVpAuthorizationRequest": "cf-purpose-parameter",
    "VCIEnsureBatchTimeClaimsNotLinkable": "cf-time-claims-linkable",
    "VCIEnsureCredentialTimeClaimsNotLinkable": "cf-time-claims-linkable",
    "VCIEnsureBatchStatusListIndicesAreUnpredictable": "cf-batch-status-privacy",
    "VCIEnsureBatchStatusReferencesAreDistinct": "cf-batch-status-privacy",
    "VCIWarnBatchStatusListUrisProvideHerdPrivacy": "cf-batch-status-privacy",
    "EnsurePARInvalidRequestOrInvalidDpopProof": "cf-dpop-at-par",
    "CheckTokenEndpointReturnedInvalidRequestGrantOrDPopProofError": "cf-dpop-at-par",
    "RequireOnlyBCP195RecommendedCiphersForTLS12": "cf-tls12-ciphers",
    "EnsureTLS12RequireBCP195Ciphers": "cf-tls12-ciphers",
    "CheckForBCP195InsecureFAPICiphers": "cf-tls12-ciphers",
    "DisallowTLS10": "cf-tls12-ciphers",
    "DisallowTLS11": "cf-tls12-ciphers",
    "VCICheckForDeferredCredentialResponse": "cf-access-token-reuse",
    "VCIValidateCredentialErrorResponse": "cf-error-codes",
    "CheckErrorFromTokenEndpointResponseErrorInvalidGrant": "cf-pkce-missing-verifier",
    "CheckTokenEndpointCacheHeaders": "cf-cache-control",
    "ExpectAccessDeniedErrorFromAuthorizationEndpointDueToUserRejectingRequest": "cf-browser-steps",
    "EnsureErrorFromAuthorizationEndpointResponse": "cf-browser-steps",
    "ExpectLoginPage": "cf-request-uri-reuse-before-auth",
    "ExpectInvalidRequestUriErrorPage": "cf-browser-steps",
    "ExpectAuthorizationRequestWithoutRequestObjectErrorPage": "cf-browser-steps",
    "WaitForExpiry": "cf-expired-request-uri",
    "VCIGetDynamicCredentialIssuerMetadata": "cf-deploy-during-tests",
    "EnsureVerifierFetchedRevocationList": "cf-status-list-fetch",
    "VP1FinalCheckEncryptionKeyNotReused": "cf-ephemeral-encryption-key",
    "VP1FinalEnsureDirectPostResponseHasRedirectUriForHaip": "cf-unknown-keys-in-responses",
    "CheckDCQLQueryCredentialFormatMatchesTestConfiguration": "cf-verifier-policy-for-suite",
    "ValidateRequestObjectAudForVP": "cf-request-object-claims",
    "ValidateRequestObjectIat": "cf-request-object-claims",
}

# Generic conditions (HTTP status checks and the like) are mapped by module instead.
TEST_HINTS = {
    "fapi2-security-profile-final-happy-flow": "cf-access-token-reuse",
    "oid4vci-1_0-issuer-happy-flow-additional-requests": "cf-access-token-reuse",
    "fapi2-security-profile-final-refresh-token": "cf-refresh-token-binding",
    "fapi2-security-profile-final-attempt-reuse-authorization-code-after-one-second": "cf-code-reuse-revocation",
    "fapi2-security-profile-final-dpop-negative-tests": "cf-dpop-htu-normalization",
    "fapi2-security-profile-final-user-rejects-authentication": "cf-browser-steps",
    "fapi2-security-profile-final-par-ensure-reused-request-uri-prior-to-auth-completion-succeeds": "cf-request-uri-reuse-before-auth",
    "fapi2-security-profile-final-par-attempt-to-use-expired-request_uri": "cf-expired-request-uri",
    "fapi2-security-profile-final-ensure-pkce-code-verifier-required": "cf-pkce-missing-verifier",
    "oid4vp-1final-verifier-present-revoked-credential": "cf-status-list-fetch",
}

TEST_RESULT_ORDER = ("FAILED", "INTERRUPTED", "WARNING", "REVIEW", "UNKNOWN", "SKIPPED", "PASSED")

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*\.?[A-Za-z0-9_-]*")
_DATA_URI_RE = re.compile(r"data:[a-z]+/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=]+")
_URL_HOST_RE = re.compile(r"(https?://)([^/\s\"'?#]+)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Hosts of the public conformance suite are kept even with --redact-hosts.
_SUITE_HOSTS = ("certification.openid.net", "localhost.emobix.co.uk", "gitlab.com", "openid.net")


def long_path(path):
    """Return a path usable on Windows beyond MAX_PATH (no-op elsewhere)."""
    path = os.path.abspath(path)
    if os.name == "nt":
        path = os.path.normpath(path)
        if not path.startswith("\\\\?\\"):
            if path.startswith("\\\\"):
                path = "\\\\?\\UNC\\" + path[2:]
            else:
                path = "\\\\?\\" + path
    return path


def short_name(path):
    """Strip the long-path prefix for display."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def iter_log_documents(inputs):
    """Yield (source_label, parsed_json) for every conformance log found."""
    for raw in inputs:
        p = long_path(raw)
        if os.path.isdir(p):
            for dirpath, _dirs, files in os.walk(p):
                for fn in sorted(files):
                    full = os.path.join(dirpath, fn)
                    yield from _read_file(full)
        elif os.path.isfile(p):
            yield from _read_file(p)
        else:
            print(f"warning: not found: {raw}", file=sys.stderr)


def _read_file(path):
    lower = path.lower()
    if lower.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as zf:
                for name in sorted(zf.namelist()):
                    if name.lower().endswith(".json"):
                        try:
                            doc = json.loads(zf.read(name).decode("utf-8"))
                        except (ValueError, UnicodeDecodeError):
                            continue
                        if _is_log(doc):
                            yield (short_name(path) + "!" + name, doc)
        except zipfile.BadZipFile:
            print(f"warning: bad zip: {short_name(path)}", file=sys.stderr)
    elif lower.endswith(".json"):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (ValueError, UnicodeDecodeError, OSError):
            return
        if _is_log(doc):
            yield (short_name(path), doc)


def _is_log(doc):
    return isinstance(doc, dict) and isinstance(doc.get("testInfo"), dict) and isinstance(doc.get("results"), list)


def scrub(text, redact_hosts=False):
    """Remove secrets and personal data from a free-text string."""
    if not isinstance(text, str):
        return text
    text = _DATA_URI_RE.sub("<data-uri>", text)
    text = _JWT_RE.sub("<jwt>", text)
    text = _EMAIL_RE.sub("<email>", text)
    if redact_hosts:
        def _host(m):
            host = m.group(2)
            if any(host == h or host.endswith("." + h) for h in _SUITE_HOSTS):
                return m.group(0)
            return m.group(1) + "<host>"
        text = _URL_HOST_RE.sub(_host, text)
    return text


def _render_value(key, value, redact_hosts):
    if key in MARKER_KEYS:
        marker = MARKER_KEYS[key]
        if marker is not None:
            return marker
        if isinstance(value, dict):
            return "keys: " + ", ".join(sorted(value.keys()))
        return "<present>"
    if key == "unknown_properties" and isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(scrub(str(item.get("path") or item.get("property")), redact_hosts))
            else:
                out.append(scrub(str(item), redact_hosts))
        return out
    if isinstance(value, (list, tuple)):
        return [scrub(v, redact_hosts) if isinstance(v, str) else v for v in value][:50]
    if isinstance(value, dict):
        # nested objects can carry tokens; keep only the key names (plus OAuth error codes)
        text = "keys: " + ", ".join(sorted(value.keys()))
        if isinstance(value.get("error"), str):
            text += "; error=" + scrub(value["error"], redact_hosts)
        return text
    if isinstance(value, str):
        v = scrub(value, redact_hosts)
        return v if len(v) <= 300 else v[:297] + "..."
    return value


def extract_details(entry, redact_hosts=False):
    details = {}
    for key in SAFE_DETAIL_KEYS + tuple(MARKER_KEYS):
        if key in entry and entry[key] not in (None, "", [], {}):
            details[key] = _render_value(key, entry[key], redact_hosts)
    return details


def variant_string(variant):
    """Compact display: the variant values in key order (the full map is kept in JSON output)."""
    if isinstance(variant, dict):
        return " ".join(str(v) for _k, v in sorted(variant.items()))
    return str(variant or "")


def summarize_doc(label, doc, redact_hosts=False):
    info = doc.get("testInfo") or {}
    alias = info.get("alias") if redact_hosts else None
    if isinstance(alias, str) and len(alias) >= 3:
        doc = json.loads(json.dumps(doc).replace(alias, "<alias>"))
    test_name = info.get("testName") or "?"
    status = info.get("status")
    result = info.get("result")
    if not result:
        result = "INTERRUPTED" if status == "INTERRUPTED" else "UNKNOWN"
    counts = {}
    findings = []
    notes = []
    for entry in doc.get("results") or []:
        if not isinstance(entry, dict):
            continue
        level = entry.get("result")
        if level:
            counts[level] = counts.get(level, 0) + 1
        src = entry.get("src") or ""
        msg = scrub((entry.get("msg") or "").strip(), redact_hosts)
        if len(msg) > 400:
            msg = msg[:397] + "..."
        if level in PROBLEM_LEVELS:
            item = {"level": level, "condition": src, "message": msg, "details": extract_details(entry, redact_hosts)}
            anchor = HINTS.get(src) or TEST_HINTS.get(test_name)
            if anchor:
                item["hint"] = "references/common-failures.md#" + anchor
            findings.append(item)
        elif level in NOTE_LEVELS:
            notes.append({"level": level, "message": msg})
    return {
        "test": test_name,
        "result": result,
        "status": status,
        "variant": variant_string(info.get("variant")),
        "variant_map": info.get("variant") if isinstance(info.get("variant"), dict) else {},
        "started": info.get("started") or "",
        "test_id": info.get("testId") or "",
        "suite_version": info.get("version") or "",
        "counts": counts,
        "findings": findings,
        "notes": notes,
        "source": scrub(os.path.basename(label.split("!")[-1]), redact_hosts),
    }


def keep_latest(rows):
    latest = {}
    for row in rows:
        key = (row["test"], row["variant"])
        if key not in latest or str(row["started"]) > str(latest[key]["started"]):
            latest[key] = row
    return list(latest.values())


def totals(rows):
    t = {}
    for row in rows:
        t[row["result"]] = t.get(row["result"], 0) + 1
    return {k: t[k] for k in sorted(t, key=lambda r: TEST_RESULT_ORDER.index(r) if r in TEST_RESULT_ORDER else 99)}


def _fmt_details(details):
    parts = []
    for k, v in details.items():
        if k == "requirements":
            continue
        if isinstance(v, list):
            v = "; ".join(str(x) for x in v)
        parts.append(f"{k}={v}")
    return " | ".join(parts)


def render_text(rows, only_problems):
    out = []
    for row in rows:
        if only_problems and not row["findings"] and row["result"] in ("PASSED", "SKIPPED"):
            continue
        out.append(f"{row['result']:<11} {row['test']}  [{row['variant']}]")
        for f in row["findings"]:
            req = ",".join(f["details"].get("requirements", []) or [])
            line = f"    {f['level']:<7} {f['condition']}"
            if req:
                line += f" ({req})"
            line += f" | {f['message']}"
            out.append(line)
            d = _fmt_details(f["details"])
            if d:
                out.append(f"            {d}")
            if f.get("hint"):
                out.append(f"            see {f['hint']}")
        for n in row["notes"]:
            out.append(f"    {n['level']:<7} {n['message']}")
    t = totals(rows)
    out.append("")
    out.append(f"{len(rows)} test(s): " + ", ".join(f"{k}={v}" for k, v in t.items()))
    return "\n".join(out) + "\n"


def _md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_markdown(rows, only_problems):
    out = ["# Conformance log summary", ""]
    t = totals(rows)
    out.append(f"{len(rows)} test(s): " + ", ".join(f"**{k}** {v}" for k, v in t.items()))
    out.append("")
    out.append("| Result | Module | Variant | Findings |")
    out.append("|---|---|---|---|")
    for row in rows:
        if only_problems and not row["findings"] and row["result"] in ("PASSED", "SKIPPED"):
            continue
        out.append(f"| {row['result']} | `{row['test']}` | {_md_escape(row['variant'])} | {len(row['findings'])} |")
    detailed = [r for r in rows if r["findings"] or r["notes"]]
    if detailed:
        out.append("")
        out.append("## Findings")
    for row in detailed:
        out.append("")
        out.append(f"### `{row['test']}` — {row['result']}")
        out.append("")
        for f in row["findings"]:
            req = ", ".join(f["details"].get("requirements", []) or [])
            head = f"- **{f['level']}** `{f['condition']}`"
            if req:
                head += f" ({req})"
            out.append(head + f": {_md_escape(f['message'])}")
            d = _fmt_details(f["details"])
            if d:
                out.append(f"  - details: {_md_escape(d)}")
            if f.get("hint"):
                out.append(f"  - see `{f['hint']}`")
        for n in row["notes"]:
            out.append(f"- {n['level']}: {_md_escape(n['message'])}")
    return "\n".join(out) + "\n"


def render_json(rows):
    return json.dumps({"tool": "oidf-log-summary", "version": VERSION, "totals": totals(rows), "tests": rows}, indent=2, ensure_ascii=False) + "\n"


def build_rows(inputs, latest=False, redact_hosts=False):
    rows = [summarize_doc(label, doc, redact_hosts) for label, doc in iter_log_documents(inputs)]
    if latest:
        rows = keep_latest(rows)
    rows.sort(key=lambda r: (str(r["started"]), r["test"]))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Summarize OpenID Foundation conformance suite logs (account data and secrets are stripped).")
    ap.add_argument("paths", nargs="+", help="log files (.json/.zip) or directories")
    ap.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    ap.add_argument("--latest", action="store_true", help="keep only the most recent run of each module+variant")
    ap.add_argument("--only-problems", action="store_true", help="hide clean PASSED/SKIPPED modules in the listing")
    ap.add_argument("--redact", "--redact-hosts", dest="redact_hosts", action="store_true",
                    help="also replace your hostnames in URLs with <host> and the suite alias with <alias> (suite hosts are kept)")
    ap.add_argument("--fail-on", choices=("FAILED", "WARNING", "REVIEW", "INTERRUPTED"), help="exit 1 if any test ended with this result or worse")
    ap.add_argument("--output", "-o", help="write to this file instead of stdout")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)

    rows = build_rows(args.paths, latest=args.latest, redact_hosts=args.redact_hosts)
    if args.format == "json":
        text = render_json(rows)
    elif args.format == "markdown":
        text = render_markdown(rows, args.only_problems)
    else:
        text = render_text(rows, args.only_problems)

    if args.output:
        with open(long_path(args.output), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles
        except (AttributeError, ValueError):
            pass
        sys.stdout.write(text)

    if not rows:
        print("warning: no conformance logs found", file=sys.stderr)
        return 2
    if args.fail_on:
        severity = {"FAILED": 0, "INTERRUPTED": 1, "WARNING": 2, "REVIEW": 3}
        limit = severity[args.fail_on]
        if any(severity.get(r["result"], 99) <= limit for r in rows):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
