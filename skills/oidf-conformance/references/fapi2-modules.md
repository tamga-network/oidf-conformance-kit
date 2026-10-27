# FAPI 2.0 Security Profile modules inside the issuer HAIP plan

`oid4vci-1_0-issuer-haip-test-plan` reuses the FAPI 2.0 SP Final server modules (`FAPI2SPFinalTestPlan.fapi2SPtestModules()`)
minus signing-only, OpenID Connect-only (nonce/`id_token`), `private_key_jwt`-only, ecosystem-specific (Brazil, CDR,
ConnectID, KSA) and grant-management modules. What remains — 1 discovery module plus 39 flow modules — runs with
`vci_haip`, `client_attestation`, `dpop`, unsigned PAR and `plain_oauth`. The **resource endpoint** is your
**credential endpoint**.

Spec shorthand as in [common-failures.md](common-failures.md). "Error page → REVIEW" means: if your server shows an error
page instead of redirecting back with an error, upload a screenshot and the module ends as REVIEW (acceptable).
Redirecting back with the right `error` (and `state`, `iss`) avoids the screenshot.

## Discovery

### `fapi2-security-profile-final-discovery-end-point-verification`
- **Checks:** AS metadata: issuer, PAR endpoint and `require_pushed_authorization_requests`, `code_challenge_methods_supported`
  incl. `S256`, `dpop_signing_alg_values_supported`, `token_endpoint_auth_methods_supported` with `attest_jwt_client_auth`
  and both client attestation alg lists (`CheckDiscEndpointClientAttestationSigningAlgValuesSupported`, `OAuth2-ATCA07-10.1`),
  `authorization_response_iss_parameter_supported`, schema check (`CheckForUnexpectedParametersInServerMetadata`, allow-list
  `server.allow_unexpected_metadata_fields`).
- **Fix:** see [client attestation algs](common-failures.md#cf-client-attestation-alg-metadata).

## Happy paths

### `fapi2-security-profile-final-happy-flow`
- **Checks:** two clients, full flow, sender-constrained access token used at the credential endpoint several times, TLS
  1.0/1.1 refused, TLS 1.3 preferred, TLS 1.2 limited to BCP 195 suites (`RequireOnlyBCP195RecommendedCiphersForTLS12`,
  FAPI2 §5.2.1), `Date` header on resource responses.
- **Typical failures:** CBC ciphers ([fix](common-failures.md#cf-tls12-ciphers)); single-use access token
  ([decision](common-failures.md#cf-access-token-reuse)).
- **Browser:** login twice.

### `fapi2-security-profile-final-user-rejects-authentication`
- The tester rejects authentication/consent; the redirect must carry `error=access_denied` (RFC 6749 §4.1.2.1).
  **Browser:** press Cancel/Deny, for each client the test opens. [Details](common-failures.md#cf-browser-steps).

### `fapi2-security-profile-final-ensure-authorization-request-without-state-success`
- `state` is optional: the flow must succeed and no `state` may come back.

### `fapi2-security-profile-final-access-token-type-header-case-sensitivity`
- `Authorization: dpop …` (lower case) must be accepted (RFC 9110 §11.1, RFC 9449 §7.1).

### `fapi2-security-profile-final-check-dpop-proof-nbf-exp`
- DPoP proofs that carry `nbf` / `exp` must still be accepted (extra claims are allowed).

### `fapi2-security-profile-final-ensure-dpopproof-with-iat-10seconds-before-succeeds`
### `fapi2-security-profile-final-ensure-dpopproof-with-iat-10seconds-after-succeeds`
- `iat` ±10 s at PAR, token and resource must be accepted (clock skew; RFC 9449 §11.1). Use a window like ±60 s.

### `fapi2-security-profile-final-ensure-dpopproof-at-par-endpoint-binding-success`
### `fapi2-security-profile-final-ensure-dpop-auth-code-binding-success`
- DPoP proof at PAR (resp. `dpop_jkt`) and the same key at the token endpoint must succeed (RFC 9449 §10, §10.1).

## DPoP binding negatives

### `fapi2-security-profile-final-ensure-mismatched-dpop-jkt-fails`
- PAR with `dpop_jkt` ≠ the PAR DPoP proof key → `400 invalid_request|invalid_dpop_proof` (`EnsurePARInvalidRequestOrInvalidDpopProof`, `DPOP-10.1`).

### `fapi2-security-profile-final-ensure-token-endpoint-fails-with-mismatched-dpop-proof-jkt`
- PAR proof key ≠ token proof key → token error (`invalid_grant`).

### `fapi2-security-profile-final-ensure-token-endpoint-fails-with-mismatched-dpop-jkt`
- `dpop_jkt` ≠ token proof key → token error. All three: [fix](common-failures.md#cf-dpop-at-par).

### `fapi2-security-profile-final-dpop-negative-tests`
- Long list of malformed proofs at the resource; mostly 400/401 expected, a few must be accepted (htu normalization,
  extra claims). [Details](common-failures.md#cf-dpop-htu-normalization).

### `fapi2-security-profile-final-ensure-holder-of-key-required`
- Token request without DPoP → error (FAPI2 §5.3.2.1: sender-constrained tokens required). Also re-checks TLS on all
  endpoints.

## State and request object handling (unsigned PAR)

### `fapi2-security-profile-final-ensure-different-state-inside-and-outside-request-object`
### `fapi2-security-profile-final-ensure-authorization-request-with-long-state`
### `fapi2-security-profile-final-state-only-outside-request-object-not-used`
- With PAR the "request object" is the pushed request. Valid outcomes: use only the pushed parameters (return the pushed
  `state`, ignore one added to the authorization URL), return a long `state` unchanged, or reject with an error. These
  usually end WARNING/REVIEW with "image no longer required" when the flow succeeds — no screenshot needed.

### `fapi2-security-profile-final-ensure-request-object-without-redirect-uri-fails`
- PAR without `redirect_uri` → PAR error (or error page → REVIEW).

### `fapi2-security-profile-final-ensure-redirect-uri-in-authorization-request`
- Same idea for the authorization request; permitted outcomes: PAR `invalid_request`, error page, or default to the
  single registered URI (RFC 6749 §3.1.2.3).

### `fapi2-security-profile-final-plain-fapi-tolerate-unregistered-redirect-uri`
- Unregistered `redirect_uri`: either allowed (RFC 9126 §2.4 permits per-request URIs for authenticated clients) or
  rejected with an error page → REVIEW. Rejecting is the safer choice.

### `fapi2-security-profile-final-ensure-unsigned-authorization-request-without-using-par-fails`
- Authorization endpoint called with all parameters in the query (no PAR) → must fail (FAPI2 §5.3.1, PAR required).
  Typically an error page → **upload screenshot → REVIEW**.

### `fapi2-security-profile-final-ensure-response-type-code-idtoken-fails`
### `fapi2-security-profile-final-ensure-response-type-token-fails`
- Only `response_type=code` is allowed (FAPI2 §5.3.2.2). Best: PAR `400 unsupported_response_type` or `invalid_request`.

## Token endpoint and code handling

### `fapi2-security-profile-final-ensure-client-id-in-token-endpoint`
- `client_id` of client 2 sent with client 1's code/attestation → `invalid_client` (or `invalid_grant`). Don't ignore
  a body `client_id` that disagrees with the authenticated client.

### `fapi2-security-profile-final-ensure-authorization-code-is-bound-to-client`
- Client 1's code redeemed by client 2 → `invalid_grant` (RFC 6749 §4.1.3).

### `fapi2-security-profile-final-attempt-reuse-authorization-code-after-one-second`
- Second redemption → `invalid_grant`; tokens from the first redemption SHOULD be revoked
  ([WARNING otherwise](common-failures.md#cf-code-reuse-revocation)).

### `fapi2-security-profile-final-ensure-token-endpoint-fails-with-expired-auth-code`
- The suite waits past the code lifetime it assumes (60 s) → `invalid_grant`. Keep code lifetime ≤ 60 s (FAPI2 §5.3.2.1
  recommends short-lived codes).

### `fapi2-security-profile-final-refresh-token`
- Refresh grant: allowed characters, binding to the client instance key under client attestation (ATCA §10.3), refusal
  without client authentication (RFC 6749 §6), refusal without DPoP proof, refusal for another client. SKIPPED if no
  refresh token is issued. [Binding](common-failures.md#cf-refresh-token-binding), [scope](common-failures.md#cf-refresh-scope),
  [`no-store`](common-failures.md#cf-cache-control).

## PAR modules

### `fapi2-security-profile-final-par-ensure-reused-request-uri-prior-to-auth-completion-succeeds`
- Visit the authorization endpoint twice with one `request_uri`; the second visit must work (FAPI2 §5.3.2.2 note 3;
  failure is only a WARNING). **Browser:** do nothing on the first visit. [Details](common-failures.md#cf-request-uri-reuse-before-auth).

### `fapi2-security-profile-final-par-attempt-reuse-request_uri`
- Reuse after the flow completed → error page or `invalid_request_uri` redirect (RFC 9126 §7.3 SHOULD one-time use;
  success is a WARNING). **Screenshot → REVIEW.**

### `fapi2-security-profile-final-par-attempt-to-use-expired-request_uri`
- Sleeps for `expires_in` then uses the `request_uri` → error. **Wait** (≈ `expires_in`, often 10 min), then screenshot.
  [Details](common-failures.md#cf-expired-request-uri).

### `fapi2-security-profile-final-par-attempt-to-use-request_uri-for-different-client`
- Client 1's `request_uri` with client 2's `client_id` at the authorization endpoint → error (RFC 9126 §4). Two visits,
  **two screenshots** if you show error pages; render HTML, not raw JSON.

### `fapi2-security-profile-final-par-authorization-request-containing-request_uri-form-param`
- `request_uri` inside the PAR body → `invalid_request` (RFC 9126 §2.1).

### `fapi2-security-profile-final-par-attempt-invalid-http-method`
- PAR with a non-POST method → `405` (RFC 9126 §2.3). A generic router 404 fails it.

### `fapi2-security-profile-final-par-ensure-pkce-required`
- PAR without `code_challenge` → error (FAPI2 §5.2.2-18).

### `fapi2-security-profile-final-ensure-pkce-code-verifier-required`
- Token request without `code_verifier` → `invalid_grant` ([details](common-failures.md#cf-pkce-missing-verifier)).

### `fapi2-security-profile-final-incorrect-pkce-code-verifier-rejected`
- Wrong verifier → `invalid_grant` (RFC 7636 §4.6); burn the code.

### `fapi2-security-profile-final-par-plain-pkce-rejected`
- `code_challenge_method=plain` → reject (FAPI2 §5.2.2-18 requires S256; RFC 7636 §4.4.1 → `invalid_request`).

### `fapi2-security-profile-final-par-without-duplicate-parameters`
- After PAR, calls the authorization endpoint with **only** `client_id` and `request_uri` → must succeed (RFC 9101 §5,
  RFC 9126 §4). Don't require the client to repeat `response_type`, `scope`, `redirect_uri` on the front channel.

## Suggested order

Discovery → happy-flow → the five DPoP success modules → DPoP negatives and holder-of-key → token/code modules → PAR
modules without browser interaction → refresh-token → the interactive ones in one sitting (`user-rejects-authentication`,
`…-without-using-par-fails`, `par-ensure-reused-request-uri…`, `par-attempt-reuse-request_uri`,
`par-attempt-to-use-request_uri-for-different-client`) → `par-attempt-to-use-expired-request_uri` last (it waits).
