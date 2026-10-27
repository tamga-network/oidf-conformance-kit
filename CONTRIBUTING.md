# Contributing

Thanks for helping other implementers get through the conformance suite. Contributions are welcome as issues and pull
requests.

## What helps most

- **New or changed modules / condition classes.** The suite changes often. If a module was added, renamed or now checks
  something else, update the plan reference and, if relevant, [common-failures.md](skills/oidf-conformance/references/common-failures.md)
  and the `HINTS` map in [scripts/oidf-log-summary.py](scripts/oidf-log-summary.py). Mention the suite commit you
  checked.
- **Failures you hit and fixed.** Add a row to the quick table and a section with: modules, condition class,
  requirement codes the suite prints, cause, fix, spec section, and class (real bug / recommended / config / expected /
  decision / suite limitation).
- **Suite limitations.** Explain why no spec requires the behaviour, and link the upstream issue if you filed one.

## Rules

1. **Spec citations.** Every "fix" must cite the spec or profile section that requires it. If the only source is the
   suite, it is a suite limitation, not a fix.
2. **Generic content.** No product names, hostnames, tenant names, keys, personal names or internal paths. Use
   `example.com` hosts and `REPLACE-…` placeholders.
3. **Never commit real logs or configs.** Conformance logs contain private keys from the suite configuration and the
   exporter's account. Tests and examples use synthetic logs only (`examples/sample-logs/`).
4. **Keep the summarizer dependency-free** (Python standard library, 3.8+) and its output safe: details are
   allow-listed; add a test with a planted secret for every new detail key you expose.
5. Run the checks before opening a pull request:

   ```bash
   python -m unittest discover -s tests -v
   claude plugin validate .
   ```

   If you change the summarizer output, regenerate the examples:

   ```bash
   cd examples
   python ../scripts/oidf-log-summary.py sample-logs -o sample-summary.txt
   python ../scripts/oidf-log-summary.py sample-logs --format markdown -o sample-summary.md
   python ../scripts/oidf-log-summary.py sample-logs --format json -o sample-summary.json
   ```

6. Add a line to [CHANGELOG.md](CHANGELOG.md) under *Unreleased*.

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately as described
in [SECURITY.md](SECURITY.md), not as issues.

## Releasing (maintainers)

Bump `version` in `.claude-plugin/plugin.json` and `CITATION.cff`, move *Unreleased* to a dated section in
`CHANGELOG.md`, then tag `vX.Y.Z` and create a GitHub release from the changelog section.

## License

By contributing you agree that your contributions are licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).
