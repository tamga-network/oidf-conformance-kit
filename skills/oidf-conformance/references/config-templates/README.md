# Suite configuration templates

Paste one of these into the **JSON** tab of "Create a new test plan" after replacing every `REPLACE-…` value. The suite
reads only the fields its modules declare; unknown fields are ignored, so keep the file small and explicit.

**Secrets:** the `d` members are private keys. Keep the filled-in files outside version control (or in a secrets store),
use keys generated only for the self-test, and trust their certificates only in the test environment. The exported
test logs contain this configuration (and the exporter's account) — treat logs as sensitive too; summarize them with
[`scripts/oidf-log-summary.py`](../../../../scripts/oidf-log-summary.py), which never prints the configuration.

## `issuer.json` — `oid4vci-1_0-issuer-haip-test-plan`

| Field | Meaning |
|---|---|
| `alias` | Becomes part of the suite callback: `https://<suite-host>/test/a/<alias>/callback`. Register that redirect URI (and the query-suffixed variant for client 2, see [common-failures](../common-failures.md#cf-redirect-uris)). One running test per alias. |
| `vci.credential_issuer_url` | Your Credential Issuer identifier; the suite fetches `/.well-known/openid-credential-issuer` from it. |
| `vci.credential_configuration_id` | The configuration the flows request (its `scope` is used in PAR). Pick one that requires key binding, otherwise `fail-missing-proof` skips. |
| `vci.allow_unexpected_credential_issuer_metadata_fields` | Names of documented extension members to suppress in the metadata schema check (matched at any depth). Leave empty first; add only real extensions. |
| `server.allow_unexpected_metadata_fields` | Same for the AS metadata (FAPI discovery module). |
| `vci.authorization_server` | Optional; only if your issuer metadata lists several `authorization_servers`. |
| `vci.credential_proof_type_hint` | Optional; proof type to use when several are offered. |
| `client.client_id`, `client2.client_id` | The `client_id` the suite uses as WIA `sub` for the two clients. Your AS must accept them with client attestation. |
| `client_attestation.issuer` | `iss` of the client attestations the suite mints. Your AS validates it against its trusted wallet providers. |
| `client_attestation.attester_jwks` | Private signing key + `x5c` the suite uses for client attestations. Trust the chain (test only). |
| `client_attestation.key_attestation_jwks` | Private key + `x5c` for key attestations (VCI Appendix D). Can be the same key as the attester. |
| `credential.trust_anchor_pem` | Root that your credential `x5c` chains to — the suite validates issued credentials against it (`HAIP-6.1`). |
| `credential.status_list_trust_anchor_pem` | Root for your status list token signer. |

For `credential_format=mdoc` the plan also asks for `credential.vical` / `credential.vical_url` or `credential.trust_anchor_pem`
(IACA).

## `verifier.json` — `oid4vp-1final-verifier-haip-test-plan`

| Field | Meaning |
|---|---|
| `alias` | Suite URLs: `https://<suite-host>/test/a/<alias>/authorize` (paste target) and per-instance status list URLs. |
| `client.request_object_trust_anchor_pem` | Root of the chain in your request object's `x5c` (your relying-party access certificate chain). |
| `credential.signing_jwk` | Private key + `x5c` the mock wallet uses to sign the credential **and** the status list. Your verifier must trust this chain in its test environment. If your verifier matches the SD-JWT `iss` to the certificate SAN, include the suite host as a `dNSName` SAN. |

For `iso_mdl`, add `credential.vical` or `credential.vical_url` per the plan form (IACA trust for the mock mdoc issuer).

## Generating the keys

See [pki.md](../pki.md) for a test root, attester / key-attestation / mock-PID leaves, and a converter to JWK with `x5c`.
