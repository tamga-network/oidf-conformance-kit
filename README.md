# OIDF Conformance Kit

[![CI](https://github.com/tamga-network/oidf-conformance-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/tamga-network/oidf-conformance-kit/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/tamga-network/oidf-conformance-kit?sort=semver)](https://github.com/tamga-network/oidf-conformance-kit/releases/latest)

**Get your OpenID4VCI issuer or OpenID4VP verifier through the OpenID Foundation conformance suite (HAIP + FAPI 2.0)
without weeks of trial and error — and with honest results.**

A [Claude Code](https://code.claude.com/docs) plugin that packages what you otherwise learn the hard way on a first full
run of the [OpenID Foundation conformance suite](https://gitlab.com/openid/conformance-suite): which plan and variants to
pick, how to fill in the suite configuration and test PKI, what each module checks and how it typically
fails, which browser steps testers get wrong, how to read the logs without leaking keys, and how to tell a real bug from
a suite limitation.

The rule it enforces: **fix for the spec, never for suite quirks, and document every deliberate deviation.**

## Who is this for

- Teams building an **OpenID4VCI credential issuer** (with its OAuth authorization server) or an **OpenID4VP verifier**
  for EUDI-style ecosystems, preparing for a HAIP self-test or an OpenID certification.
- Engineers who received a pile of FAILURE / WARNING / REVIEW results and need to know which ones are real bugs.
- Reviewers who want a pre-flight code checklist before anyone opens the suite.

You don't need prior experience with the suite. You do need a test deployment the suite can reach over the internet.

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

Update later with `/plugin marketplace update oidf-conformance-kit`. For local development:
`claude --plugin-dir ./oidf-conformance-kit`.

## 5-minute quick start

### Issuer (`oid4vci-1_0-issuer-haip-test-plan`)

1. **Pre-flight** — in your issuer repo, ask Claude:
   *"Run the OIDF pre-flight on this repo for the issuer HAIP plan."* The `oidf-preflight` skill writes an
   OK / RISK / UNKNOWN report with file references (metadata shapes, DPoP at PAR, token endpoint, TLS ciphers, …).
2. **Test PKI** — generate a throwaway root, attester and key-attestation keys with the openssl recipe in
   [pki.md](skills/oidf-conformance/references/pki.md).
3. **Configure** — copy [config-templates/issuer.json](skills/oidf-conformance/references/config-templates/issuer.json),
   replace every `REPLACE-…` value ([field guide](skills/oidf-conformance/references/config-templates/README.md)), then
   ask Claude: *"Walk me through creating the issuer HAIP plan with this config."*
4. **Run and summarize** — run the modules in the order the `oidf-conformance` skill gives, export the logs from the
   plan page, then:

   ```bash
   python scripts/oidf-log-summary.py ./logs --latest --only-problems
   ```

5. **Fix** — ask Claude: *"Use the oidf-fixer agent on ./logs."* It groups findings by root cause, classifies them and
   proposes spec-cited fixes with regression tests. Redeploy, re-run only the affected modules, repeat.

### Verifier (`oid4vp-1final-verifier-haip-test-plan`)

1. *"Run the OIDF pre-flight on this repo for the verifier HAIP plan."* (section G: request object, `x509_hash`,
   ephemeral encryption key, DCQL, response endpoint, KB-JWT, status lists).
2. Create a verifier test policy that requests exactly what the suite presents, and register the suite's root as a
   trusted issuer in the test environment only ([verifier-plan.md](skills/oidf-conformance/references/verifier-plan.md)).
3. Fill [config-templates/verifier.json](skills/oidf-conformance/references/config-templates/verifier.json), create the
   plan, and run the modules — the skill tells you which ones need a screenshot (REVIEW) and which pass on a `4xx`.
4. Summarize and fix as above.

## What's inside

| Component | Path | What it does |
|---|---|---|
| Skill `oidf-conformance` | [skills/oidf-conformance/SKILL.md](skills/oidf-conformance/SKILL.md) | End-to-end workflow: plan & variants → configuration → run order → browser steps & REVIEW screenshots → logs → summary → triage → fix → re-run → publish |
| Skill `oidf-preflight` | [skills/oidf-preflight/SKILL.md](skills/oidf-preflight/SKILL.md) | ~60-item code checklist to run before the first suite run; writes an OK/RISK/UNKNOWN report |
| Agent `oidf-fixer` | [agents/oidf-fixer.md](agents/oidf-fixer.md) | Reads logs via the summarizer, classifies findings, maps them to the references and proposes or applies spec-backed fixes with tests |
| Issuer plan reference | [references/issuer-plan.md](skills/oidf-conformance/references/issuer-plan.md) | Every VCI module of `oid4vci-1_0-issuer-haip-test-plan` — checks, spec refs, typical failures, fixes |
| FAPI 2.0 reference | [references/fapi2-modules.md](skills/oidf-conformance/references/fapi2-modules.md) | The 40 FAPI 2.0 Security Profile modules that run inside the issuer plan |
| Verifier plan reference | [references/verifier-plan.md](skills/oidf-conformance/references/verifier-plan.md) | Every module of `oid4vp-1final-verifier-haip-test-plan`, and how 4xx vs 200 outcomes map to PASSED/REVIEW |
| Common failures | [references/common-failures.md](skills/oidf-conformance/references/common-failures.md) | Symptom → condition class → cause → fix table (metadata shapes, locales, schema cascade, DPoP at PAR, TLS ciphers, refresh binding, status lists, ephemeral keys, …) |
| Config templates | [references/config-templates/](skills/oidf-conformance/references/config-templates/README.md) | Redacted suite JSON for the issuer and verifier plans, field by field |
| Test PKI | [references/pki.md](skills/oidf-conformance/references/pki.md) | openssl recipe for a test root, attester and mock-PID keys, and PEM → JWK with `x5c` |
| eudi-dev reference | [references/eudi-dev.md](skills/oidf-conformance/references/eudi-dev.md) | Complementing the suite with the open-source eudi-dev test wallet: EU ARF checks the suite does not do (access and registration certificates, over-asking, trusted lists), end-to-end and CI recipes, typical findings |
| Log summarizer | [scripts/oidf-log-summary.py](scripts/oidf-log-summary.py) | Per-module results and every FAILURE/WARNING/REVIEW with condition class and key details; text, Markdown or JSON; strips account data and secrets; `--fail-on` for CI |
| Examples | [examples/](examples/) | Synthetic logs and the summarizer's output for them |

Scope: the **issuer** (`oid4vci-1_0-issuer-haip-test-plan`) and **verifier** (`oid4vp-1final-verifier-haip-test-plan`)
plans. Wallet plans need a device build and are not covered yet. Module names and condition classes were checked against
the conformance-suite master of 2026-10-26; the suite evolves quickly, so confirm on the plan page.

## Example session

Synthetic logs in [examples/sample-logs/](examples/sample-logs/) run through the summarizer
(`python scripts/oidf-log-summary.py examples/sample-logs`); excerpt of
[examples/sample-summary.txt](examples/sample-summary.txt):

```text
FAILED      oid4vci-1_0-issuer-metadata-test  [client_attestation sd_jwt_vc vci_haip]
    WARNING CheckForUnexpectedParametersInCredentialIssuerMetadata (OID4VCI-1FINAL-12.2.3) | Unknown properties were found in the OID4VCI Credential Issuer metadata.
            unknown_properties=$.credential_configurations_supported.example_pid.credential_metadata.display[0].lang; $.credential_configurations_supported.example_pid.display
            see references/common-failures.md#cf-issuer-metadata-unknown-properties
    FAILURE CheckDiscEndpointClientAttestationSigningAlgValuesSupported (OAuth2-ATCA07-10.1) | attest_jwt_client_auth is supported but required fields are missing
            missing_fields=client_attestation_signing_alg_values_supported; client_attestation_pop_signing_alg_values_supported
            see references/common-failures.md#cf-client-attestation-alg-metadata
FAILED      oid4vci-1_0-issuer-batch-issuance  [client_attestation sd_jwt_vc vci_haip unsigned plain_oauth dpop wallet_initiated plain]
    FAILURE VCIEnsureBatchTimeClaimsNotLinkable (SDJWT-10.1) | The batch credentials share a precise, high-entropy time claim [iat, exp] which lets verifiers correlate the credentials.
            precise_time_claims=iat; exp | iat_distinct_values=[1792600765] | exp_distinct_values=[1855672765]
            see references/common-failures.md#cf-time-claims-linkable
REVIEW      oid4vp-1final-verifier-happy-flow  [x509_hash sd_jwt_vc request_uri_signed direct_post.jwt haip]
    WARNING CheckForUnexpectedParametersInVpAuthorizationRequest | Unknown parameters were found in the authorization request.
            unknown_params=purpose
            see references/common-failures.md#cf-purpose-parameter
...
7 test(s): FAILED=4, REVIEW=1, SKIPPED=1, PASSED=1
```

Every finding points at the reference section that explains the cause and the spec-backed fix. The `oidf-fixer` agent
then turns this into a plan such as: *"real bug — `display` and `lang` are pre-Final shapes; move display into
`credential_metadata.display` and use `locale` (VCI §12.2.4); add a metadata test"*, and *"recommended — drop `purpose`,
put it in `verifier_info`"*. Markdown and JSON versions: [sample-summary.md](examples/sample-summary.md),
[sample-summary.json](examples/sample-summary.json).

## FAQ

**Is a passing self-test an OpenID certification?**
No. Anyone can run the suite against their own deployment and get results — that is a self-test. Certification is a
separate step with the OpenID Foundation: you submit published results and a declaration, and the Foundation lists the
certified deployment. See the [certification programme](https://openid.net/certification/) and its
[fees](https://openid.net/certification/fees/). This kit helps with both, but it does not certify anything.

**Should I publish my test plan?**
Publishing a plan makes it public. With *everything* the detailed logs go out too — **including the full plan
configuration, i.e. every private key and client secret you pasted into it**; *summary* publishes results only. Either
way, before publishing rotate (revoke and replace) every test key used in that configuration and never reuse it
anywhere else. Use throwaway keys from [pki.md](skills/oidf-conformance/references/pki.md), never
production keys.

**Is it safe to share logs with Claude or attach them to an issue?**
Raw exported logs contain the same configuration plus the exporter's account and tokens. Work from the summarizer
output: it prints only allow-listed fields, replaces JWTs, data URIs and e-mail addresses, never prints configuration or
account data, and with `--redact` also hides your hostnames and the plan alias. Keep raw logs and filled-in configs out of
version control (the repo's `.gitignore` shows the patterns).

**The suite flags something no spec requires. What now?**
Don't change correct code. Confirm with the references, classify it as a *suite limitation*, document it in your results
and report it upstream. Example: the cascading `unevaluatedProperties` warning in
[common-failures.md](skills/oidf-conformance/references/common-failures.md#cf-schema-cascade).

**The suite passes. Is my issuer or verifier ready for EU wallets?**
Not necessarily. The suite tests the protocols; EU wallets also check access and registration certificates, over-asking
and trusted lists. Run an ARF-aware counterpart next to it — see [eudi-dev.md](skills/oidf-conformance/references/eudi-dev.md)
for how to use the open-source eudi-dev test wallet for that, also in CI.

**Does it work with other AI tools or without Claude?**
The references are plain Markdown and the summarizer is a standalone Python script (standard library only), so both are
usable on their own. The skills and agent are written for Claude Code.

**Which suite version is this for?**
Module names and condition classes were checked against the conformance-suite master of 2026-10-26. If a module or
condition was renamed, please [open an issue](https://github.com/tamga-network/oidf-conformance-kit/issues/new/choose).

## Requirements

- Claude Code with plugin support.
- Python 3.8+ for the summarizer (standard library only). `cryptography` only for the optional PEM → JWK snippet.
- openssl for the test PKI recipe.

## Contributing

Corrections for new or renamed modules, failures you hit and fixed, and documented suite limitations are very welcome.
Every fix must cite the spec section that requires it, and nothing may contain real logs, keys or hostnames. Read
[CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md); report security issues privately as
described in [SECURITY.md](SECURITY.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

```bash
python -m unittest discover -s tests -v    # summarizer tests (synthetic logs only) + manifest and link checks
claude plugin validate .                   # plugin and marketplace manifests
```

## License and credits

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE).

Maintained by [Tamga Network](https://tamga.network).

Not affiliated with or endorsed by the OpenID Foundation. "OpenID" is a trademark of the OpenID Foundation. A self-test
with the conformance suite is not an OpenID certification.

---

## Türkçe özet

**OIDF Conformance Kit**, OpenID Foundation uyum test aracında (conformance suite) OpenID4VCI belge veren (issuer) ve
OpenID4VP doğrulayıcı (verifier) servislerini HAIP ve FAPI 2.0 planlarıyla sınamak için bir Claude Code eklentisidir.

- **Kimin için:** AB EUDI tarzı ekosistemler için issuer ya da verifier geliştiren, HAIP öz-testine veya OpenID
  sertifikasına hazırlanan ekipler.
- **İçinde:** adım adım iş akışı, her test modülünün ne denetlediği ve nasıl düzeltileceği, ilk koşudan önce kod kontrol
  listesi, test loglarını gizli bilgi sızdırmadan özetleyen bir betik ve bulguları sınıflandırıp standarda dayalı düzeltme
  öneren bir ajan.
- **Tamamlayıcı:** OIDF aracı AB'ye özgü ARF kurallarını (erişim ve kayıt sertifikası, fazla istek, güven listeleri)
  denetlemez; açık kaynak eudi-dev test cüzdanıyla nasıl tamamlanacağı `references/eudi-dev.md`'de.
- **Temel kural:** düzeltmeyi standart için yap, test aracının kendine özgü beklentisi için değil; bilinçli her farkı yaz.
- **Dikkat:** öz-test sertifika değildir. Bir planı yayımlamak, plan ayarındaki özel anahtarları da herkese açar —
  yayımlamadan önce test anahtarlarını değiştirin.
- **Kurulum:** `/plugin marketplace add tamga-network/oidf-conformance-kit` ve
  `/plugin install oidf-conformance-kit@oidf-conformance-kit`. Lisans: Apache-2.0.
