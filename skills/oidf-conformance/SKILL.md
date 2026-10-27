---
name: oidf-conformance
description: Run the OpenID Foundation conformance suite against an OpenID4VCI 1.0 issuer (with its OAuth authorization server) or an OpenID4VP 1.0 verifier under HAIP and FAPI 2.0 — choose the plan and variants, prepare the suite configuration and test PKI, run modules in a sensible order, handle browser steps and REVIEW screenshots, download and summarize logs, triage every finding (real bug / config / expected / suite limitation), fix for the spec and re-run, then publish. Use when someone mentions the OIDF conformance suite, certification.openid.net, oid4vci-1_0-issuer-haip-test-plan, oid4vp-1final-verifier-haip-test-plan, FAPI2 conformance modules, a FAILED/WARNING/REVIEW conformance result, or a downloaded test-log JSON/zip.
---

# OIDF conformance testing (OpenID4VCI / OpenID4VP, HAIP, FAPI 2.0)

You help a team get a clean, honest result from the OpenID Foundation conformance suite. The suite is a strong
oracle for the specs but it is software too: **fix for the spec, never for suite quirks**, and write down every
deliberate deviation.

References (load the one you need, they are long):

- [references/issuer-plan.md](references/issuer-plan.md) — `oid4vci-1_0-issuer-haip-test-plan`, every VCI module
- [references/fapi2-modules.md](references/fapi2-modules.md) — the 40 FAPI 2.0 modules inside the issuer plan
- [references/verifier-plan.md](references/verifier-plan.md) — `oid4vp-1final-verifier-haip-test-plan`, every module
- [references/common-failures.md](references/common-failures.md) — symptom → condition class → cause → fix
- [references/config-templates/](references/config-templates/README.md) — redacted suite configuration templates
- [references/pki.md](references/pki.md) — test root, attester and mock-issuer keys with openssl
- Log summarizer: `python "${CLAUDE_PLUGIN_ROOT}/scripts/oidf-log-summary.py" <logs>`
- Before the first run: the `oidf-preflight` skill. For log triage and fixes: the `oidf-fixer` agent.

## Rules

1. **Spec first.** A finding is fixed in code only when a spec or profile requirement (MUST/SHALL; HAIP, FAPI 2.0)
   or a well-founded SHOULD (privacy, security) supports the change. Cite the section in the commit and the test.
2. **Never change correct behaviour to satisfy the suite.** If the suite checks something no spec requires, or cannot
   be configured around a legitimate extension, classify it as *suite limitation*, keep your code, document it, and
   prepare an upstream issue (gitlab.com/openid/conformance-suite).
3. **Test-only relaxations are explicit.** If the suite's mock wallet/issuer cannot satisfy an ecosystem rule (a claim
   your production policy requires), add a named switch that defaults to strict, enable it only in the test environment,
   and record it. Trust the suite's test keys only there.
4. **Decisions are recorded.** When the spec allows several behaviours and the suite exercises one you don't implement
   (e.g. access-token reuse, refresh-token binding), that is a product decision: write it down (ADR or equivalent)
   before changing code.
5. **Secrets stay private.** Filled-in configs contain private keys; exported logs contain the configuration and the
   exporter's account. Never commit, paste or quote them. Share only the summarizer output.
6. **A self-test is not a certification.** Say "self-test" when you publish unless the team actually certifies.

## Workflow

### 1. Pick the plan and variants

| Target | Plan | Choose | Fixed by the plan |
|---|---|---|---|
| Issuer + AS | `oid4vci-1_0-issuer-haip-test-plan` ("OpenID for Verifiable Credential Issuance 1.0 Final/HAIP: Test an issuer") | credential format `sd_jwt_vc` or `mdoc`; flow `wallet_initiated` (or `issuer_initiated` with a credential offer endpoint) | `vci_haip`, `client_attestation`, `dpop`, unsigned PAR, authorization code |
| Verifier | `oid4vp-1final-verifier-haip-test-plan` ("OpenID for Verifiable Presentations 1.0 Final/HAIP: Test a verifier") | credential format `sd_jwt_vc` or `iso_mdl`; response mode `direct_post.jwt` | `haip`, `x509_hash`, `request_uri_signed` |

Wallet plans (`oid4vp-1final-wallet-haip-test-plan`, the VCI wallet plan) test a wallet app and need a device build;
they are out of scope here. Avoid plans marked *alpha*. Confirm module names on the plan page — the suite changes
weekly; this kit was checked against master of 2026-10-26.

Hosted suite: `https://demo.certification.openid.net` (log in with Google/GitLab; API token only after login). A local
suite (Docker) uses `https://localhost.emobix.co.uk:8443`.

### 2. Run the pre-flight

Run the `oidf-preflight` skill on the codebase. It catches most first-run failures (metadata shapes, DPoP binding,
TLS ciphers, error codes, `no-store`, refresh binding, verifier encryption keys, status list fetching) in minutes
instead of a day of suite runs.

### 3. Prepare the configuration

1. Generate the test PKI ([pki.md](references/pki.md)).
2. Fill [issuer.json](references/config-templates/issuer.json) or [verifier.json](references/config-templates/verifier.json);
   keep the filled file outside the repository.
3. Configure the test environment of the system under test:
   - **Issuer:** trust the suite's attester/key-attestation chain; register the callbacks
     `https://<suite-host>/test/a/<alias>/callback` and `…/callback?dummy1=lorem&dummy2=ipsum` for both client ids;
     make the configuration in `vci.credential_configuration_id` require key binding.
   - **Verifier:** a policy that requests exactly one credential of the format under test (EU PID `urn:eudi:pid:1` for
     `sd_jwt_vc`); trust the mock PID issuer chain (and its status list signer); allow fetching the status list from
     the suite host during verification.
4. Allow-list only documented extensions (`vci.allow_unexpected_credential_issuer_metadata_fields`,
   `server.allow_unexpected_metadata_fields`). Start with an empty list so you see everything once.
5. **Freeze deployments** of the target for the duration of the run (a restart turns modules into 502 failures).

### 4. Create the plan and run modules

- Create the plan with the JSON; save the plan URL. The configuration of an existing plan can't be edited — to change
  it, create a new plan.
- Run **one module at a time per alias**; starting another interrupts the first ("alias conflict").
- Order: issuer → metadata, FAPI discovery, happy flow, negative VCI, the rest of VCI, FAPI modules, interactive FAPI
  modules, expired-`request_uri` last ([issuer-plan.md](references/issuer-plan.md#suggested-run-order)); verifier →
  happy flow, other positives, fast negatives, revoked / wrong-vct ([verifier-plan.md](references/verifier-plan.md#suggested-run-order)).
- If the happy flow fails, stop and fix it before running anything else.

### 5. Browser steps and screenshots (REVIEW)

- Flow modules open your authorization page: complete login/consent (twice for multiple-client modules).
- `user-rejects-authentication`: press **Cancel/Deny**, never approve.
- `par-ensure-reused-request-uri-prior-to-auth-completion-succeeds`: on the first visit **do nothing**; complete on the second.
- `par-attempt-to-use-expired-request_uri`: let it wait (~`expires_in`, often 10 minutes).
- Error-page modules and verifier modules answered with `200`: take a screenshot showing the page and the address bar
  and upload it in the module's upload box. The module then ends as **REVIEW** — that is a normal, passing outcome
  that a human reviews at certification time. Some state modules say "image no longer required"; skip the upload then.
- Verifier plan: create a **new request for every module** and paste the full `openid4vp://…` link into the test page.

### 6. Download the logs

Plan page → **Export** (zip of all modules) or per-module "Download log". Store them outside version control
(`.gitignore` them). They contain your configuration (private keys) and your suite account.

### 7. Summarize

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/oidf-log-summary.py" path/to/logs --latest
python "${CLAUDE_PLUGIN_ROOT}/scripts/oidf-log-summary.py" path/to/logs --latest --format markdown --redact -o summary.md
python "${CLAUDE_PLUGIN_ROOT}/scripts/oidf-log-summary.py" path/to/logs --format json   # for tooling
```

It reads folders and `.zip` exports, handles Windows long paths, prints per-module results and every
FAILURE/WARNING/REVIEW with condition class, requirement codes and key details (`unknown_properties` paths, expected vs
actual errors, cipher suites, time-claim deltas), and links known conditions to
[common-failures.md](references/common-failures.md). Account data, configuration, tokens, JWTs and screenshots are never
printed; `--redact` also hides your hostnames and the alias.

### 8. Triage every finding

For each FAILURE and WARNING (and each REVIEW you didn't expect), decide one class and write it in a results table:

| Class | Test | Action |
|---|---|---|
| **real bug** | a MUST/SHALL (or HAIP/FAPI requirement) is violated | fix + regression test citing the section |
| **recommended** | SHOULD / privacy / security recommendation | fix unless a documented reason says otherwise |
| **config** | suite config, environment, deployment, tester's browser step | fix the config/procedure; re-run |
| **expected** | unsupported optional variant (SKIPPED), documented extension | document |
| **decision** | spec allows it; suite exercises a behaviour you chose not to support | record a decision, then fix or document |
| **suite limitation** | suite requires something no spec does, or can't be configured around a valid extension | keep code; document; prepare an upstream issue |

Use the `oidf-fixer` agent to do this in bulk from the logs. Ask: *would a different, spec-conformant wallet or
verifier break on our current behaviour?* If yes, it is not a suite quirk.

### 9. Fix, test, redeploy, repeat

Fix in small commits with spec citations, add unit/integration tests that reproduce the suite's request, deploy to the
test environment, and re-run **only** the affected modules ("Repeat Test"), plus the happy flow. Iterate until no
FAILED remains and every WARNING/REVIEW has a written reason.

### 10. Publish

Plan page → **Publish** → *summary* (results only) unless you deliberately want to publish everything (*everything*
also exposes detailed logs and configuration). **Before publishing, rotate every key and secret in the plan
configuration** (revoke the test keys in your test environment and replace them) — treat anything that was ever in a
suite configuration as public from then on. Publish a short results page next to it: plan, variants, suite version
(`testInfo.version` in the logs) and date, per-module outcome, and a "deliberate deviations and suite limitations"
section. Formal certification is a separate step with the OpenID Foundation.

## Results table template

```markdown
| # | Module | Result | Finding (condition) | Class | Spec | Action / commit | Status |
|---|---|---|---|---|---|---|---|
| 01 | oid4vci-1_0-issuer-metadata-test | WARNING | CheckForUnexpectedParametersInCredentialIssuerMetadata: credential_metadata.<ext> | suite limitation | VCI §12.2.4; <ext spec> | documented; upstream issue drafted | accepted |
```
