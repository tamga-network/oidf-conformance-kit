# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Reference `eudi-dev.md`: complementing the suite with the open-source eudi-dev test wallet — the EU ARF checks the suite
  does not do (access and registration certificates, over-asking by format, trusted lists and their JAdES signature),
  running it against a test deployment, an end-to-end presentation with the suite's mock PID issuer, a CI recipe and a
  table of typical findings with their classification. Linked from the README, the FAQ and the skill's workflow step 9.

## [0.1.0] - 2026-10-27

First public release.

### Added

- Skill `oidf-conformance`: end-to-end workflow for the issuer (`oid4vci-1_0-issuer-haip-test-plan`) and verifier
  (`oid4vp-1final-verifier-haip-test-plan`) plans — plan and variants, configuration, run order, browser steps and
  REVIEW screenshots, logs, triage, fix, re-run, publish (with key rotation before publishing).
- Skill `oidf-preflight`: code checklist (metadata, PAR/PKCE, DPoP and client attestation, token, credential and nonce
  endpoints, transport, verifier) with an OK/RISK/UNKNOWN report template.
- Agent `oidf-fixer`: classifies findings (real bug · recommended · config · expected · decision · suite limitation) and
  proposes spec-cited fixes with tests.
- References: per-module issuer, FAPI 2.0 and verifier plan notes; common failures table, including the
  `VP1FinalCheckEncryptionKeyNotReused` ephemeral-key check, `VCIValidateDisplayLocales` /
  `VCIWarnOnNonCanonicalDisplayLocales` with locale normalization guidance, the batch status-list checks
  (`VCIEnsureBatchStatusReferencesAreDistinct`, `VCIEnsureBatchStatusListIndicesAreUnpredictable`,
  `VCIWarnBatchStatusListUrisProvideHerdPrivacy`) and the cascading `unevaluatedProperties` suite limitation.
- Redacted suite configuration templates and an openssl test-PKI recipe.
- `scripts/oidf-log-summary.py`: dependency-free log summarizer (text, Markdown, JSON; `--latest`, `--only-problems`,
  `--redact`, `--fail-on`) that strips account data and secrets; synthetic example logs and outputs.
- CI on Linux and Windows (Python 3.8 and 3.13); code of conduct, security policy, issue and pull request templates.

Checked against the conformance-suite master of 2026-10-26.

[Unreleased]: https://github.com/tamga-network/oidf-conformance-kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tamga-network/oidf-conformance-kit/releases/tag/v0.1.0
