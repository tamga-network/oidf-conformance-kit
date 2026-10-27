# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report them privately through GitHub:
[Security → Report a vulnerability](https://github.com/tamga-network/oidf-conformance-kit/security/advisories/new).

Examples of what we treat as security issues:

- the log summarizer printing a secret, private key, token, account detail or configuration value it should strip;
- guidance in a skill, reference or the fixer agent that would weaken a deployment's security (for example a "fix" that
  disables a check in production rather than behind a test-only switch);
- anything in the plugin that runs code or reaches the network unexpectedly.

Include the kit version, what you observed and, if possible, a **synthetic** log that reproduces it. Never attach real
conformance logs or configurations — they contain private keys.

We aim to acknowledge reports within 5 working days and to publish a fix and an advisory once it is resolved. Credit is
given in the advisory unless you prefer otherwise.

## Supported versions

Only the latest release receives fixes.

## Out of scope

Vulnerabilities in the OpenID Foundation conformance suite itself (report those to the
[conformance suite tracker](https://gitlab.com/openid/conformance-suite/-/issues) as a confidential issue) and in your
own issuer or verifier.
