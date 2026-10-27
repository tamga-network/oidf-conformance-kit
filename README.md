# OIDF Conformance Kit

A [Claude Code](https://code.claude.com/docs) plugin for getting an OpenID4VCI issuer or an OpenID4VP verifier through the
[OpenID Foundation conformance suite](https://gitlab.com/openid/conformance-suite) — HAIP and FAPI 2.0 plans — with
honest results: **fix for the spec, never for suite quirks, and document every deliberate deviation.**

It packages what you learn the hard way on a first full run: which plan and variants to pick, how to fill in the suite
configuration and test PKI, what each module checks and how it typically fails, which browser steps testers get wrong,
how to read the logs without leaking keys, and how to tell a real bug from a suite limitation.

## What's inside

| Component | Path | What it does |
|---|---|---|
| Skill `oidf-conformance` | [skills/oidf-conformance/SKILL.md](skills/oidf-conformance/SKILL.md) | End-to-end workflow: plan & variants → configuration → run order → browser steps & REVIEW screenshots → logs → summary → triage → fix → re-run → publish |
| Issuer plan reference | [references/issuer-plan.md](skills/oidf-conformance/references/issuer-plan.md) | `oid4vci-1_0-issuer-haip-test-plan`: every VCI module — checks, spec refs, typical failures, fixes |
| FAPI 2.0 reference | [references/fapi2-modules.md](skills/oidf-conformance/references/fapi2-modules.md) | The 40 FAPI 2.0 Security Profile modules that run inside the issuer plan |
| Verifier plan reference | [references/verifier-plan.md](skills/oidf-conformance/references/verifier-plan.md) | `oid4vp-1final-verifier-haip-test-plan`: every module, how 4xx vs 200 outcomes map to PASSED/REVIEW |
| Common failures | [references/common-failures.md](skills/oidf-conformance/references/common-failures.md) | Symptom → condition class → cause → fix table (metadata shapes, DPoP at PAR, TLS ciphers, refresh binding, status lists, …) |
| Config templates | [references/config-templates/](skills/oidf-conformance/references/config-templates/README.md) | Redacted suite JSON for the issuer and verifier plans, field by field |
| Test PKI | [references/pki.md](skills/oidf-conformance/references/pki.md) | openssl recipe for a test root, attester and mock-PID keys, and PEM → JWK with `x5c` |
| Skill `oidf-preflight` | [skills/oidf-preflight/SKILL.md](skills/oidf-preflight/SKILL.md) | Code checklist to run before the first suite run; writes an OK/RISK/UNKNOWN report |
| Agent `oidf-fixer` | [agents/oidf-fixer.md](agents/oidf-fixer.md) | Reads logs via the summarizer, classifies findings, maps them to the references and proposes or applies spec-backed fixes with tests |
| Log summarizer | [scripts/oidf-log-summary.py](scripts/oidf-log-summary.py) | Per-module results and every FAILURE/WARNING/REVIEW with condition class and key details; text, Markdown or JSON; strips account data and secrets |
| Examples | [examples/](examples/) | Synthetic logs and the summarizer's output for them |

Scope: the **issuer** (`oid4vci-1_0-issuer-haip-test-plan`) and **verifier** (`oid4vp-1final-verifier-haip-test-plan`)
plans. Wallet plans need a device build and are not covered yet. Module names and condition classes were checked
against the conformance-suite master of 2026-10-26; the suite evolves quickly, so confirm on the plan page.

## Install

In Claude Code:

```
/plugin marketplace add tamga-network/oidf-conformance-kit
/plugin install oidf-conformance-kit@oidf-conformance-kit
```

or from a shell:

```bash
claude plugin marketplace add tamga-network/oidf-conformance-kit
claude plugin install oidf-conformance-kit@oidf-conformance-kit
```

For local development: `claude --plugin-dir ./oidf-conformance-kit`.

## Quick start

1. Before touching the suite, ask Claude: *"Run the OIDF pre-flight on this repo for the issuer HAIP plan."* — the
   `oidf-preflight` skill reports likely failures with file references.
2. Generate test keys ([pki.md](skills/oidf-conformance/references/pki.md)), fill the
   [config template](skills/oidf-conformance/references/config-templates/README.md), and follow the
   `oidf-conformance` skill to create the plan and run the modules.
3. Export the logs from the plan page and summarize them:

   ```bash
   python scripts/oidf-log-summary.py ./logs --latest
   python scripts/oidf-log-summary.py ./logs --latest --format markdown --redact -o summary.md
   ```

4. Ask Claude: *"Use the oidf-fixer agent on ./logs."* It groups findings by root cause, classifies them (real bug ·
   recommended · config · expected · decision · suite limitation) and proposes fixes with tests and spec citations.
5. Fix, redeploy to the test environment, re-run only the affected modules, repeat; publish the summary.

Sample output for synthetic logs: [examples/sample-summary.md](examples/sample-summary.md).

## Safety

Conformance logs contain the suite configuration — including the **private keys** you gave the suite — plus the
exporter's account and tokens. Keep logs and filled-in configs out of version control. The summarizer prints only
allow-listed fields, replaces JWTs, data URIs and e-mail addresses, never prints the configuration or account data, and
with `--redact` also hides your hostnames and the alias.

## Requirements

- Claude Code with plugin support.
- Python 3.8+ for the summarizer (standard library only). `cryptography` only for the optional PEM → JWK snippet.
- openssl for the test PKI recipe.

## Development

```bash
python -m unittest discover -s tests -v    # summarizer tests (synthetic logs only) + manifest and link checks
claude plugin validate .                   # plugin and marketplace manifests
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE).

Not affiliated with or endorsed by the OpenID Foundation. "OpenID" is a trademark of the OpenID Foundation. A
self-test with the conformance suite is not an OpenID certification.

Maintained by Tamga Network.

---

## Türkçe özet

**OIDF Conformance Kit**, OpenID Foundation uyum test aracında (conformance suite) OpenID4VCI belge veren ve OpenID4VP
doğrulayıcı servislerini HAIP ve FAPI 2.0 planlarıyla sınamak için bir Claude Code eklentisidir. İçinde: adım adım iş
akışı, her test modülünün ne denetlediği ve nasıl düzeltileceği, ilk koşudan önce kod kontrol listesi, test loglarını
gizli bilgi sızdırmadan özetleyen bir betik ve bulguları sınıflandırıp standarda dayalı düzeltme öneren bir ajan.
Temel kural: **düzeltmeyi standart için yap, test aracının kendine özgü beklentisi için değil; bilinçli her farkı yaz.**
Kurulum: `/plugin marketplace add tamga-network/oidf-conformance-kit` ve
`/plugin install oidf-conformance-kit@oidf-conformance-kit`. Lisans: Apache-2.0.
