## What and why

<!-- What does this change, and which suite module / condition / spec section is it about? -->

## Checklist

- [ ] Every fix cites the spec or profile section that requires it (suite-only behaviour is documented as a suite limitation).
- [ ] Generic content only: no product names, hostnames (use `example.com`), tenants, keys, personal names or internal paths.
- [ ] No real logs or filled-in configurations; tests and examples use synthetic logs.
- [ ] Suite version or commit checked: <!-- e.g. master of YYYY-MM-DD -->
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] `claude plugin validate .` passes (if manifests changed).
- [ ] If the summarizer output changed: examples regenerated and a planted-secret test added for any new detail key.
- [ ] `CHANGELOG.md` updated under *Unreleased*.
