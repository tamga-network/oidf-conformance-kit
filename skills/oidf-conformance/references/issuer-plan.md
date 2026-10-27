# Issuer plan — `oid4vci-1_0-issuer-haip-test-plan`

Display name: **"OpenID for Verifiable Credential Issuance 1.0 Final/HAIP: Test an issuer"** (certifiable). Do not pick
the plain `oid4vci-1_0-issuer-test-plan` or anything marked *alpha* if you want the HAIP profile. Checked against the
conformance-suite source (`VCIIssuerTestPlanHaip`, master of 2026-10-26); the suite moves fast — re-check module names
in the plan page before a run.

## Variants

| Variant parameter | Choose | Fixed by the plan |
|---|---|---|
| `credential_format` (Credential Format) | `sd_jwt_vc` (`dc+sd-jwt`) or `mdoc` (`mso_mdoc`) | — |
| `vci_authorization_code_flow_variant` | `wallet_initiated` (default) or `issuer_initiated` (needs a credential offer endpoint) | — |
| `fapi_profile` | — | `vci_haip` |
| `client_auth_type` | — | `client_attestation` |
| `sender_constrain` | — | `dpop` |
| `fapi_request_method` | — | `unsigned` (PAR, no JAR) |
| `vci_grant_type` | — | `authorization_code` (pre-authorized code is not applicable under HAIP) |
| `vci_credential_encryption` | — | `plain` for most modules, `encrypted` for three |
| `authorization_request_type`, `openid`, `fapi_response_mode` | — | `simple`, `plain_oauth`, `plain_response` |

Module count with these variants: **63** = 2 metadata + 18 plain VCI + 3 encrypted VCI + 1 FAPI discovery + 39 FAPI 2.0
modules ([fapi2-modules.md](fapi2-modules.md)). Configuration: [config-templates/issuer.json](config-templates/issuer.json).

## Before the first run

- The suite acts as the **wallet**: it mints a client attestation (WIA) and PoP with `client_attestation.attester_jwks`,
  and key attestations with `client_attestation.key_attestation_jwks`. Your AS must trust that signer — in a test
  environment only. See [pki.md](pki.md) and [common-failures.md](common-failures.md#cf-test-only-relaxations).
- Register the suite callbacks for both client ids, including the query-suffixed one
  ([redirect URIs](common-failures.md#cf-redirect-uris)).
- Put the trust anchor that signs your **credentials** in `credential.trust_anchor_pem` and the one that signs your
  **status lists** in `credential.status_list_trust_anchor_pem` (`EnsureCredentialTrustAnchorConfigured`,
  `EnsureStatusListTrustAnchorConfigured`, `HAIP-6.1`).
- Browser step: every flow module opens your authorization endpoint. Have a test identity ready that can be completed
  in a few clicks; the suite waits.
- The suite adds random unknown parameters to authorization, token, credential and notification requests; you must
  ignore them (happy-flow summary).

## Module reference

Legend — **Checks**: what the module asserts. **Spec**: requirement codes the suite prints. **Typical failures** → **fix**.
**Browser/screenshot**: what the tester does.

### 1. `oid4vci-1_0-issuer-metadata-test`
- **Checks:** Credential Issuer metadata at `/.well-known/openid-credential-issuer` (VCI §12.2.2) and the AS metadata
  (RFC 8414 §3): required fields (`VCICheckRequiredMetadataFields`), HTTPS URLs, `credential_issuer` matches,
  `authorization_servers`, `nonce_endpoint` present (`VCIValidateNonceEndpointInIssuerMetadata`, `HAIP-4.1-5`),
  `credential_signing_alg_values_supported`, `proof_types_supported` and their algs, `scope` syntax (RFC 6749 §3.3),
  display locales, batch issuance metadata, encryption metadata, schema check for unknown members.
  AS side: PAR required, PKCE `S256`, DPoP algs, `attest_jwt_client_auth` with both alg lists, `authorization_response_iss_parameter_supported`.
- **Spec:** `OID4VCI-1FINAL-12.2.2`, `-12.2.3`, `-12.2.4`, `RFC8414-3.1`, `OAuth2-ATCA07-10.1`, `HAIP-4.1-5`.
- **Typical failures:** missing client attestation alg lists → [fix](common-failures.md#cf-client-attestation-alg-metadata);
  unknown properties → [fix / allow-list / cascade](common-failures.md#cf-issuer-metadata-unknown-properties); invalid
  locale tags; `vc+sd-jwt`.
- **Browser:** none.

### 2. `oid4vci-1_0-issuer-metadata-test-signed`
- **Checks:** as 1, plus signed metadata: request with `Accept: application/jwt` must return a JWT
  (`EnsureContentTypeApplicationJwt`, `VCIDecodeSignedCredentialIssuerMetadata`, VCI §12.2.2). Use `typ`
  `openidvci-issuer-metadata+jwt`, sign with a key whose chain the wallet can validate, keep claims identical to the JSON.
- **Typical failures:** signed variant not implemented (JSON returned) → serve both by content negotiation.

### 3. `oid4vci-1_0-issuer-happy-flow`
- **Checks:** metadata → PAR (with client attestation + DPoP) → authorization (browser) → token (DPoP) → nonce endpoint →
  proof (+ key attestation) → credential → credential validation (signature, `cnf`, status, `vct`, format) →
  notification (if offered). VCI §5–§8, §11.
- **Typical failures:** unknown keys in the response ([fix](common-failures.md#cf-unknown-keys-in-responses)); credential
  signature chain not under `credential.trust_anchor_pem`; time claims precise; status list not reachable or signed by
  an untrusted key.
- **Browser:** complete the login/consent once.

### 4. `oid4vci-1_0-issuer-happy-flow-additional-requests`
- **Checks:** happy flow plus extra credential requests with the same access token and FAPI headers
  (`x-fapi-interaction-id`, IPv6 `x-fapi-customer-ip-address`, `Accept` variants), and TLS checks on the endpoints.
- **Typical failures:** single-use access tokens ([decision](common-failures.md#cf-access-token-reuse)); TLS 1.2 CBC
  ciphers ([fix](common-failures.md#cf-tls12-ciphers)).

### 5. `oid4vci-1_0-issuer-happy-flow-multiple-clients`
- **Checks:** two complete flows with `client` and `client2` (second callback query-suffixed); compares the two
  credentials' time claims (`VCIEnsureCredentialTimeClaimsNotLinkable`, `SDJWT-10.1`).
- **Typical failures:** second PAR 400 (callback not registered) → [redirect URIs](common-failures.md#cf-redirect-uris);
  time claims advance by the real gap → [round](common-failures.md#cf-time-claims-linkable).
- **Browser:** complete the login **twice**.

### 6. `oid4vci-1_0-issuer-happy-flow-skip-notification`
- **Checks:** the flow works when the wallet never calls the notification endpoint (VCI §11 is optional for the wallet).
- **Typical failures:** credential stays "pending" and a later request fails — don't make issuance depend on notification.

### 7. `oid4vci-1_0-issuer-batch-issuance`
- **Checks:** several proofs in one request (`proofs.jwt` array, VCI §8.2; `batch_credential_issuance.batch_size` in
  metadata): one credential per proof, each bound to its proof key, keys distinct (`VCIEnsureBatchBindingKeysAreDistinct`,
  `VCIEnsureBatchBindingKeysMatchSentProofKeys`), same dataset, distinct disclosure salts, unlinkable time claims,
  distinct and unpredictable status indices.
- **Typical failures:** precise `iat`/`exp` shared across the batch (FAILURE) → [fix](common-failures.md#cf-time-claims-linkable);
  sequential status indices → [fix](common-failures.md#cf-batch-status-privacy); fewer credentials than proofs
  (`VCIWarnIfFewerCredentialsThanRequestedProofs`).

### 8. `oid4vci-1_0-issuer-fail-invalid-nonce`
- **Checks:** a proof with a random `c_nonce` must be rejected with `invalid_nonce` (VCI §8.3.1.2, `VCIInjectRandomCNonce`).
- **Typical failures:** `invalid_proof` instead of `invalid_nonce`; nonce not checked at all.

### 9. `oid4vci-1_0-issuer-fail-invalid-jwt-proof-signature`
- **Checks:** corrupted proof JWT signature → `invalid_proof`.

### 10. `oid4vci-1_0-issuer-fail-invalid-key-attestation-signature`
- **Checks:** corrupted key attestation signature (VCI Appendix D; HAIP) → `invalid_proof`.
- **Typical failures:** key attestation verified only when a policy flag is set; chain not validated.

### 11. `oid4vci-1_0-issuer-fail-invalid-client-attestation-signature`
- **Checks:** WIA signature corrupted → PAR (first authenticated request) must fail with `400`/`401` and
  `invalid_client` | `invalid_request` | `invalid_client_attestation` (ATCA §6.2).

### 12. `oid4vci-1_0-issuer-fail-invalid-client-attestation-pop-signature`
- **Checks:** PoP signature corrupted → as 11.

### 13. `oid4vci-1_0-issuer-fail-client-attestation-exp-in-past`
- **Checks:** WIA `exp` 10 minutes in the past → as 11, or `use_fresh_attestation`.

### 14. `oid4vci-1_0-issuer-fail-client-attestation-no-sub`
- **Checks:** WIA without `sub` → as 11.

### 15. `oid4vci-1_0-issuer-fail-client-attestation-pop-wrong-aud`
- **Checks:** PoP `aud` is not your issuer/AS identifier → as 11.
- **Typical failures:** `aud` not checked, or checked against the endpoint URL only; accept the AS issuer identifier
  (ATCA allows it) and be consistent.

### 16. `oid4vci-1_0-issuer-fail-mismatched-client-attestation-pop-key`
- **Checks:** PoP signed with a key other than the WIA `cnf.jwk` → as 11.

### 17. `oid4vci-1_0-issuer-fail-missing-proof`
- **Checks:** credential request without `proofs` for a configuration that requires binding → `invalid_proof`
  (skipped if the configuration needs no proof).

### 18. `oid4vci-1_0-issuer-fail-unknown-credential-configuration` (plain)
- **Checks:** unknown `credential_configuration_id` → `unknown_credential_configuration` (VCI §8.3.1.2).
- **Typical failures:** generic `invalid_credential_request`; 502 during a deploy ([config](common-failures.md#cf-deploy-during-tests)).

### 19. `oid4vci-1_0-issuer-fail-unknown-credential-identifier`
- **Checks:** unknown `credential_identifier` → `unknown_credential_identifier`. Applies even if you never issue
  `credential_identifiers` in the token response.
- **Typical failures:** `invalid_credential_request` → [error codes](common-failures.md#cf-error-codes).

### 20. `oid4vci-1_0-issuer-fail-on-access-token-in-query`
- **Checks:** after a normal credential request, repeats it with the access token in a query parameter → must fail
  (`DisallowAccessTokenInQuery`, FAPI2 §5.3.4, `FAPI2-SP-FINAL-5.3.4-2`).

### 21. `oid4vci-1_0-issuer-happy-flow` (encrypted)
### 22. `oid4vci-1_0-issuer-fail-unknown-credential-configuration` (encrypted)
### 23. `oid4vci-1_0-issuer-fail-unsupported-encryption-algorithm` (encrypted)
- **Checks:** credential response/request encryption (VCI §10, `credential_response_encryption` /
  `credential_request_encryption` in metadata); 23 expects `invalid_encryption_parameters`.
- **Outcome when you don't advertise encryption:** **SKIPPED** ("Credential encryption is not supported by the credential
  issuer…"). That is expected; encryption is optional in HAIP for issuance.

### 24–63. FAPI 2.0 Security Profile modules

`fapi2-security-profile-final-discovery-end-point-verification` and 39 more, run against your AS and credential endpoint
(as the protected resource) with DPoP and client attestation. See [fapi2-modules.md](fapi2-modules.md).

## Suggested run order

1. 1–2 (metadata; no browser). Fix everything here first — later modules re-read the same metadata.
2. 24 (FAPI discovery).
3. 3 (happy flow). If it fails, stop and fix; nearly everything else builds on it.
4. 8–20 (negative VCI; fast, mostly no extra browser work beyond the login).
5. 4–7 (additional requests, multiple clients, skip-notification, batch).
6. FAPI modules in the order of [fapi2-modules.md](fapi2-modules.md), saving the slow/interactive ones
   (`user-rejects-authentication`, reused/expired `request_uri`, error-page modules) for a dedicated sitting.
7. 21–23 last (they skip unless you support encryption).

## Typical final picture

All PASSED except: WARNING on 1–2 only for documented, allow-list-proof extensions ([cascade](common-failures.md#cf-schema-cascade));
REVIEW on modules that end on an error page (screenshots uploaded); SKIPPED for the encrypted variants if not supported
and for `refresh-token` if refresh tokens are not issued for the suite's scope.
