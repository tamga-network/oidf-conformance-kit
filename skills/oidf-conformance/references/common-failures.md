# Common failures — symptom → condition → cause → fix

Findings that show up again and again when an OpenID4VCI issuer (plus its authorization server) or an OpenID4VP
verifier meets the OpenID Foundation conformance suite for the first time. Every row names the **condition class**
the suite logs in the `src` field, so you can grep a log or the summary from
[`scripts/oidf-log-summary.py`](../../../scripts/oidf-log-summary.py) straight to the right section.

Classification used throughout this kit:

| Class | Meaning | What you do |
|---|---|---|
| **real bug** | The spec (MUST/SHALL, or a profile requirement of HAIP / FAPI 2.0) says otherwise | Fix the code, add a regression test |
| **recommended** | A SHOULD, or a privacy/security recommendation the suite reports as WARNING | Fix it unless you have a written reason not to |
| **config** | Suite configuration, test environment, or the tester's browser step | Fix the configuration or the procedure, not the code |
| **expected** | A variant you don't support, or a deliberate, documented extension | Leave it; document it in your results |
| **suite limitation** | The suite checks something no spec requires, or cannot be configured around a legitimate extension | Never change correct code for it; document it and report it upstream |

Spec abbreviations: **VCI** OpenID4VCI 1.0 Final · **VP** OpenID4VP 1.0 Final · **HAIP** OpenID4VC High Assurance
Interoperability Profile 1.0 · **FAPI2** FAPI 2.0 Security Profile (Final) · **ATCA** OAuth 2.0 Attestation-Based
Client Authentication (draft -07, as the suite cites it) · **SD-JWT VC** draft-ietf-oauth-sd-jwt-vc · **TSL**
draft-ietf-oauth-status-list (Token Status List). Section numbers follow the requirement codes the suite prints (e.g.
`OID4VCI-1FINAL-8.3.1`, `OAuth2-ATCA07-10.1`, `FAPI2-SP-FINAL-5.2.2`); drafts renumber, so check the version you
implement.

## Quick table

| Symptom (module / message) | Condition class | Usual cause | Fix | Class |
|---|---|---|---|---|
| metadata / discovery: alg values missing | `CheckDiscEndpointClientAttestationSigningAlgValuesSupported` | AS metadata advertises `attest_jwt_client_auth` but not the two alg lists | [add both lists](#cf-client-attestation-alg-metadata) | real bug |
| metadata: "Unknown properties were found" | `CheckForUnexpectedParametersInCredentialIssuerMetadata` | pre-Final shapes (`display` at configuration level, `lang`), or real extensions | [fix shapes, allow-list extensions](#cf-issuer-metadata-unknown-properties) | real bug / config |
| metadata: standard fields (`scope`, `proof_types_supported`…) reported unknown | same | one extension member inside `credential_metadata` breaks the schema branch | [schema cascade](#cf-schema-cascade) | suite limitation |
| metadata: locale errors | `VCIValidateDisplayLocales`, `VCIWarnOnNonCanonicalDisplayLocales` | invalid/duplicate BCP 47 tags, `DE` instead of `de` | [locales](#cf-issuer-metadata-unknown-properties) | real bug / recommended |
| happy flows: "Unexpected keys in credential response" | `VCIValidateNoUnknownKeysInCredentialResponse` | extra top-level member in the credential response | [move it out of the response](#cf-unknown-keys-in-responses) | recommended |
| verifier: "Direct post response object contains unexpected keys" | `ValidateDirectPostResponse` | extra member next to `redirect_uri` | [only `redirect_uri`](#cf-unknown-keys-in-responses) | recommended |
| verifier: "Unknown parameters were found in the authorization request" (`purpose`) | `CheckForUnexpectedParametersInVpAuthorizationRequest` | non-VP request parameter such as `purpose` | [use `verifier_info`](#cf-purpose-parameter) | recommended |
| batch / multiple clients: "share a precise, high-entropy time claim" | `VCIEnsureBatchTimeClaimsNotLinkable`, `VCIEnsureCredentialTimeClaimsNotLinkable` | `iat`/`exp`/`nbf` (or mdoc `validityInfo`) to the second | [round or randomize](#cf-time-claims-linkable) | real bug (batch) / recommended |
| batch: status list indices predictable / shared | `VCIEnsureBatchStatusListIndicesAreUnpredictable`, `VCIEnsureBatchStatusReferencesAreDistinct`, `VCIWarnBatchStatusListUrisProvideHerdPrivacy` | sequential index allocation, one list per credential | [random indices, shared lists](#cf-batch-status-privacy) | real bug (HAIP) / recommended |
| `ensure-mismatched-dpop-jkt-fails`: PAR returned 201 | `EnsurePARInvalidRequestOrInvalidDpopProof` | DPoP proof at PAR ignored, `dpop_jkt` not compared | [bind DPoP at PAR](#cf-dpop-at-par) | real bug |
| token endpoint accepts a different DPoP key | `CheckTokenEndpointReturnedInvalidRequestGrantOrDPopProofError` | code not bound to the PAR key | [bind code to key](#cf-dpop-at-par) | real bug |
| "Server accepted a cipher that is not on the list of permitted ciphers" | `RequireOnlyBCP195RecommendedCiphersForTLS12` | CBC / SHA-1 suites enabled in TLS 1.2 | [ECDHE + AES-GCM only](#cf-tls12-ciphers) | real bug |
| FAPI2 happy flow: second credential request 401 / "neither credentials nor transaction_id" | `VCICheckForDeferredCredentialResponse`, `EnsureHttpStatusCodeIs200or201` | access token is single-use | [allow reuse within lifetime](#cf-access-token-reuse) | decision (spec allows reuse) |
| `fail-unknown-credential-identifier`: expected error not found | `VCIValidateCredentialErrorResponse` | generic `invalid_credential_request` instead of the specific code | [error codes table](#cf-error-codes) | real bug |
| `ensure-pkce-code-verifier-required`: `'error' field has unexpected value` | `CheckErrorFromTokenEndpointResponseErrorInvalidGrant` | `invalid_request` for a missing `code_verifier` | [`invalid_grant`](#cf-pkce-missing-verifier) | real bug (suite expectation follows RFC 7636 §4.6) |
| "token endpoint response does not contain 'cache-control' header" | `CheckTokenEndpointCacheHeaders` | `no-store` only on success, or not at all | [every token response](#cf-cache-control) | real bug |
| refresh-token: "refresh token is bound to another DPoP key" | `CheckIfTokenEndpointResponseError` | refresh token bound to the DPoP key | [bind to the client instance key](#cf-refresh-token-binding) | real bug |
| refresh-token: SKIPPED "No refresh token was issued" / refreshed token unusable | (module skip) / `CheckIfTokenEndpointResponseError` | refresh tokens only for a companion scope; refresh before first credential request fails | [refresh scope rules](#cf-refresh-scope) | expected / real bug |
| code reuse: resource still 200 after second code use | `EnsureHttpStatusCodeIs4xx` (WARNING) | tokens from the first redemption not revoked | [revoke on reuse](#cf-code-reuse-revocation) | recommended |
| dpop-negative-tests: htu with upper-case host or `:443` rejected | `EnsureHttpStatusCodeIs200or201` (WARNING, `RFC3986-6.2.2`) | byte comparison of `htu` | [normalize](#cf-dpop-htu-normalization) | recommended |
| credential endpoint 401 without challenge | (no single condition; seen in logs and reviews) | missing `WWW-Authenticate: DPoP` | [challenge header](#cf-www-authenticate) | real bug |
| two credential requests with the same `c_nonce` both succeed | (concurrency; not a dedicated module) | non-atomic nonce consumption | [atomic consume](#cf-nonce-race) | real bug |
| user-rejects-authentication: "error parameter not found" | `ExpectAccessDeniedErrorFromAuthorizationEndpointDueToUserRejectingRequest` | tester approved instead of cancelling | [browser steps](#cf-browser-steps) | config |
| reused request_uri before auth: "authenticated on the initial visit" | (module exception) / `ExpectLoginPage` | tester completed login on the first visit | [do nothing on first visit](#cf-request-uri-reuse-before-auth) | config |
| expired request_uri: `WaitForExpiry` "Interrupted while sleeping" | `WaitForExpiry` | test stopped during the `expires_in` wait | [wait it out](#cf-expired-request-uri) | config |
| "Stopping test due to alias conflict" | (INTERRUPTED) | a second test started with the same alias | [one test at a time](#cf-alias-conflict) | config |
| "Unable to fetch credential issuer metadata" / 502 | `VCIGetDynamicCredentialIssuerMetadata` | service restarted during a deployment | [no deploys during runs](#cf-deploy-during-tests) | config |
| verifier revoked test: list not fetched | `EnsureVerifierFetchedRevocationList` | verifier only uses pre-fetched status lists | [fetch at verification time](#cf-status-list-fetch) | real bug (revoked) / recommended |
| verifier: encryption key reused across requests | `VP1FinalCheckEncryptionKeyNotReused` (FAILURE under HAIP) | static `client_metadata.jwks` | [ephemeral key per request](#cf-ephemeral-encryption-key) | real bug |
| verifier: DCQL format/type mismatch | `CheckDCQLQueryCredentialFormatMatchesTestConfiguration` | no policy that requests what the suite presents | [test policy](#cf-verifier-policy-for-suite) | config |
| verifier: request object `aud` / `iat` warnings | `ValidateRequestObjectAudForVP`, `ValidateRequestObjectIat` | claims missing from the request object | [request object claims](#cf-request-object-claims) | recommended |
| PAR 400 for the second client | (PAR error) | query-suffixed callback not registered | [redirect URIs](#cf-redirect-uris) | config |
| suite's attestation rejected for a missing claim your policy requires | `invalid_client` / `invalid_proof` at PAR or credential | suite-minted WIA/key attestation lacks an ecosystem claim | [test-only relaxation](#cf-test-only-relaxations) | config |

---

<a id="cf-client-attestation-alg-metadata"></a>
## Client attestation signing alg values missing from AS metadata

- **Seen in:** `oid4vci-1_0-issuer-metadata-test`, `…-metadata-test-signed`, `fapi2-security-profile-final-discovery-end-point-verification`.
- **Condition:** `CheckDiscEndpointClientAttestationSigningAlgValuesSupported` (FAILURE, `OAuth2-ATCA07-10.1`). If
  `token_endpoint_auth_methods_supported` contains `attest_jwt_client_auth`, the AS metadata must also carry non-empty
  arrays `client_attestation_signing_alg_values_supported` and `client_attestation_pop_signing_alg_values_supported`.
- **Fix:** publish both, e.g. `["ES256"]`, in `/.well-known/oauth-authorization-server` (RFC 8414) of every AS that
  accepts attestation-based client authentication. Add a unit test that asserts both keys whenever the method is listed.

<a id="cf-issuer-metadata-unknown-properties"></a>
## Unknown properties in Credential Issuer metadata

- **Condition:** `CheckForUnexpectedParametersInCredentialIssuerMetadata` (WARNING, `OID4VCI-1FINAL-12.2.3`). The log
  entry has `unknown_properties`, each with `property` and a JSONPath `path`. The summary script prints the paths.
- **Fix real shape errors first** — most "unknown" fields are pre-Final shapes:
  - `display` directly on a credential configuration: in VCI §12.2.4 it lives in `credential_metadata.display`
    (and claim descriptions in `credential_metadata.claims`).
  - `lang` inside OpenID4VCI display objects: VCI uses **`locale`** (BCP 47). `lang` is the SD-JWT VC *type metadata*
    word — keep `lang` in your `vct` type metadata documents, use `locale` only in the issuer metadata.
  - `format: "vc+sd-jwt"`: Final uses `dc+sd-jwt` (`VCICheckForOldSdJwtFormatInCredentialConfigurations`).
  - Locale validity: `VCIValidateDisplayLocales` (FAILURE) requires well-formed, registered BCP 47 tags and only one
    display object per language identifier (VCI §12.2.4); `VCIWarnOnNonCanonicalDisplayLocales` (WARNING) flags casing
    such as `DE` or `en-us`. See [locale normalization](#cf-locale-normalization).
- **Then allow-list real extensions** (an ecosystem-defined member such as one from an ETSI profile or an EUDI rulebook):
  add the member *names* to `vci.allow_unexpected_credential_issuer_metadata_fields` in the plan configuration. The
  name matches at any depth. The configuration of an existing plan cannot be edited, so create a new plan.
  For extra members in the **authorization server** metadata, the FAPI discovery module uses
  `server.allow_unexpected_metadata_fields` (`CheckForUnexpectedParametersInServerMetadata`).
- **Do not** remove a member the ecosystem requires just to silence the warning. Document it.

<a id="cf-locale-normalization"></a>
### Locale normalization

Normalize every display `locale` once, where the issuer metadata is built, from a single source of truth:

- **Canonical case** (RFC 5646 §2.1.1): language lower case, script title case, region upper case — `de`, `en-US`,
  `sr-Latn-RS`, `zh-Hant-TW`. Anything else is a `VCIWarnOnNonCanonicalDisplayLocales` WARNING.
- **Compare after normalizing.** Tags are case-insensitive, so `en-us` and `en-US` are the *same* language identifier
  and two display objects carrying them are a duplicate (`VCIValidateDisplayLocales` FAILURE). `en` and `en-US` are
  different identifiers and may coexist.
- **Registered subtags only.** A country code is not a language code: Danish is `da` (not `dk`), Ukrainian `uk` (not
  `ua`), Greek `el` (not `gr`), Swedish `sv` (not `se`). Private-use or made-up primary subtags fail validation.
- **Scope.** Apply this to the OpenID4VCI issuer metadata (`credential_metadata.display[].locale`,
  `credential_metadata.claims[].display[].locale`, top-level `display[].locale`). Leave SD-JWT VC type metadata (`lang`)
  and credential contents alone; validate them with the same rules but don't rename the member.

A small helper (split on `-`, lower-case the first subtag, title-case 4-letter subtags, upper-case 2-letter region
subtags after the first) plus a unit test that fails on duplicates after normalization covers both checks.

<a id="cf-schema-cascade"></a>
### Cascading `unevaluatedProperties` warning (suite limitation)

If the warning lists *standard* configuration fields (`scope`, `cryptographic_binding_methods_supported`,
`proof_types_supported`) only for configurations whose `credential_metadata` carries an extension member, you are
looking at a schema cascade, not at a bug: the suite's `credential_issuer_metadata-1_0.json` declares
`credential_metadata` with `additionalProperties: false` inside the first `allOf` branch. The extension makes that branch
fail; under JSON Schema 2020-12 a failing subschema yields no annotations, so its properties count as *unevaluated* and
the outer `unevaluatedProperties: false` reports them. The allow-list is applied to the reported names after
evaluation, so it cannot undo the cascade.

What to do: confirm the only genuinely unknown member is your extension (remove it locally and re-validate against the
suite schema), accept the WARNING, write it down as a suite limitation, and file an issue at
`https://gitlab.com/openid/conformance-suite/-/work_items/new` with the configuration excerpt, the observed
`unknown_properties` and the spec reference for the extension. Never move a standard field or drop an ecosystem field to
make this warning disappear.

<a id="cf-unknown-keys-in-responses"></a>
## Unknown keys in credential, error and direct_post responses

- **Credential response** — `VCIValidateNoUnknownKeysInCredentialResponse` (WARNING, `OID4VCI-1FINAL-8.3`): the suite
  expects only `credentials`, `transaction_id`, `notification_id`, `interval`. `VCIValidateNoUnknownKeysInCredentialErrorResponse`
  does the same for error bodies (`error`, `error_description`). An extra top-level member that carries extension data
  is better served as its **own credential configuration** (advertised in metadata, requested with the same access
  token in a second credential request) or a separate endpoint, so the standard response stays clean.
- **Verifier `direct_post` response** — `ValidateDirectPostResponse` (WARNING, `OID4VP-1FINAL-8.2`): the body must be
  `{}` or `{"redirect_uri": "…"}`. Put any extra state (a one-time view key, a session hint) into the `redirect_uri`
  itself. Under HAIP the `redirect_uri` is mandatory: `VP1FinalEnsureDirectPostResponseHasRedirectUriForHaip`
  (FAILURE, `HAIP-5.1`); `ValidateDirectPostResponseRedirectUriWhenPresent` checks its shape.

<a id="cf-purpose-parameter"></a>
## `purpose` (or other non-VP members) in the authorization request

- **Condition:** `CheckForUnexpectedParametersInVpAuthorizationRequest` (WARNING). Known parameters are VP §5.1/§5.2
  plus JAR claims (`client_id`, `response_uri`, `response_type`, `response_mode`, `nonce`, `state`, `dcql_query`,
  `client_metadata`, `verifier_info`, `request_uri_method`, `wallet_nonce`, `aud`, `iss`, `iat`, `nbf`, `exp`, `jti`, …).
- **Fix:** do not invent request parameters. A human-readable purpose belongs in the relying party's registration
  information (`verifier_info`, VP §5.1, e.g. an ETSI TS 119 475 registration certificate carrying the intended use)
  or in the trusted registry the wallet consults. Make sure your wallet reads it from there before you drop the
  parameter.

<a id="cf-time-claims-linkable"></a>
## Time claims make credentials linkable

- **Conditions:** `VCIEnsureBatchTimeClaimsNotLinkable` (batch issuance, FAILURE), `VCIEnsureCredentialTimeClaimsNotLinkable`
  (multiple clients, WARNING with 2 s tolerance). Requirement `SDJWT-10.1` — RFC 9901 (SD-JWT) §10.1: time information
  in credentials of a batch must be randomized or rounded so verifiers cannot correlate copies.
- **Typical log:** `precise_time_claims=["iat","exp"]`, `iat_distinct_values=[<one value at issuance instant>]`, or
  `delta_iat_seconds` equal to `delta_response_time_seconds`.
- **Fix:** round `iat`, `nbf` *and* `exp` (exp derived from a rounded base) down to the hour or day, or add per-credential
  random offsets; apply the same to mdoc MSO `validityInfo.signed/validFrom/validUntil`. Edge case: if the rounded
  `iat` would fall before the signing certificate's `notBefore` (or before the issuer's authorization start), keep the
  later instant so the credential stays verifiable. Test: two issuances a few seconds apart produce identical or
  uncorrelated time claims.

<a id="cf-batch-status-privacy"></a>
## Status list references in a batch

- `VCIEnsureBatchStatusReferencesAreDistinct` (FAILURE): two credentials share `uri`+`idx` — a double allocation (TSL)
  and HAIP §6.1 ("Each Credential MUST have its own unique, unpredictable status list index").
- `VCIEnsureBatchStatusListIndicesAreUnpredictable` (FAILURE under HAIP): three or more indices in an arithmetic
  progression. Allocate indices randomly (TSL privacy considerations recommend non-sequential allocation).
- `VCIWarnBatchStatusListUrisProvideHerdPrivacy` (WARNING): every credential points at a different list URI. Share large
  lists across holders; differ only by index.

<a id="cf-dpop-at-par"></a>
## DPoP binding at PAR (`dpop_jkt`) and at the token endpoint

- **Modules:** `fapi2-…-ensure-mismatched-dpop-jkt-fails`, `…-ensure-token-endpoint-fails-with-mismatched-dpop-proof-jkt`,
  `…-ensure-token-endpoint-fails-with-mismatched-dpop-jkt`, and the success twins `…-dpopproof-at-par-endpoint-binding-success`,
  `…-dpop-auth-code-binding-success`.
- **Conditions:** `EnsurePARInvalidRequestOrInvalidDpopProof` (PAR must answer 400 `invalid_request` or
  `invalid_dpop_proof`), `CheckTokenEndpointReturnedInvalidRequestGrantOrDPopProofError` (token endpoint must return an
  error with `error` set).
- **Spec:** RFC 9449 §10 (authorization code binding via `dpop_jkt`) and §10.1 (DPoP with PAR: a DPoP proof sent to the
  PAR endpoint binds the code; if both a proof and `dpop_jkt` are present they must match).
- **Fix:** at PAR, verify any DPoP proof (signature, `htm`/`htu`, `iat`, `jti`), compute its JWK SHA-256 thumbprint
  (RFC 7638) and compare with `dpop_jkt` if present → `400 invalid_dpop_proof` on mismatch; store the thumbprint with
  the request and the resulting code. At the token endpoint, a proof with a different key → `400 invalid_grant`. Note
  the success modules: a correct binding must still pass (a common regression is rejecting proofs at PAR that carry no
  `dpop_jkt`).

<a id="cf-tls12-ciphers"></a>
## TLS 1.2 cipher suites

- **Conditions:** `RequireOnlyBCP195RecommendedCiphersForTLS12` (FAILURE, `FAPI2-SP-FINAL-5.2.2`), `EnsureTLS12RequireBCP195Ciphers`,
  `DisallowTLS10` / `DisallowTLS11`, `EnsureTLS13OrLater` (WARNING), `CheckForBCP195InsecureFAPICiphers`.
- **Spec:** FAPI2 §5.2.1 (TLS 1.2 or later, BCP 195), BCP 195 / RFC 9325 §4.2 recommended TLS 1.2 suites.
- **Allowed in TLS 1.2:** `ECDHE-ECDSA-AES128-GCM-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`,
  `ECDHE-ECDSA-AES256-GCM-SHA384`, `ECDHE-RSA-AES256-GCM-SHA384`. Disable CBC and SHA-1 suites; keep TLS 1.3 enabled.
  The suite probes every endpoint host it talks to (issuer, AS, credential endpoint).
- **Example (nginx):** `ssl_protocols TLSv1.2 TLSv1.3;` and
  `ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;`
- **Verify:** `openssl s_client -connect host:443 -tls1_2 -cipher ECDHE-ECDSA-AES128-SHA` must fail;
  `-cipher ECDHE-ECDSA-AES128-GCM-SHA256` must succeed.

<a id="cf-access-token-reuse"></a>
## Single-use access tokens break the happy flows

- **Modules:** `fapi2-security-profile-final-happy-flow`, `oid4vci-1_0-issuer-happy-flow-additional-requests`. Both send
  several credential requests (with FAPI headers, IPv6 customer address, UTF-8 `Accept` variants) with the *same* access
  token.
- **Symptom:** second request `401 invalid_token` → `VCICheckForDeferredCredentialResponse` "contains neither credentials
  nor transaction_id", or `EnsureHttpStatusCodeIs200or201`.
- **Spec position:** VCI does not make access tokens single-use; a token may authorize several credential requests
  within its lifetime (VCI §8, §6). Treat this as a design decision: allow reuse within the (short) lifetime, keep the
  scope/`authorization_details` restriction, keep the sender constraint (same DPoP key), and cap the number of credentials
  per token if your privacy model needs it. Record the decision before you change the behaviour.

<a id="cf-error-codes"></a>
## Error codes the suite expects

| Situation | Expected | Spec |
|---|---|---|
| Unknown `credential_configuration_id` | `400 unknown_credential_configuration` | VCI §8.3.1.2 |
| Unknown `credential_identifier` (including "we never issue identifiers") | `400 unknown_credential_identifier` | VCI §8.3.1.2 |
| Missing proof / bad proof signature / bad key attestation signature | `400 invalid_proof` | VCI §8.3.1.2 |
| Stale or unknown `c_nonce` in the proof | `400 invalid_nonce` | VCI §8.3.1.2, §7 |
| Unsupported encryption parameters | `400 invalid_encryption_parameters` | VCI §8.3.1.2 |
| Bad client attestation / PoP (signature, `sub`, `aud`, key mismatch) | `400`/`401` `invalid_client` (also accepted: `invalid_request`, `invalid_client_attestation`) | ATCA §6.2 |
| Expired client attestation | as above, or `use_fresh_attestation` | ATCA §6.2 |
| Missing `code_verifier` / wrong verifier / reused or expired code / code bound to other client or key | `400 invalid_grant` | RFC 6749 §5.2, RFC 7636 §4.6, RFC 9449 §10 |
| `client_id` in the token request different from the authenticated client | `invalid_client` (or `invalid_grant`) | RFC 6749 §5.2 |
| `plain` PKCE, missing PKCE, `response_type` other than `code`, `request_uri` inside PAR body, unknown/duplicate parameters | `400 invalid_request` at PAR (or an error page) | FAPI2 §5.2.2, RFC 7636 §4.4.1, RFC 9126 §2.1 |
| PAR called with GET/PUT | `405` | RFC 9126 §2.3 |
| DPoP proof mismatch at PAR | `400 invalid_dpop_proof` | RFC 9449 §10.1 |
| Missing/invalid/expired access token or DPoP proof at the credential endpoint | `401` + `WWW-Authenticate: DPoP error="invalid_token"` / `"invalid_dpop_proof"` | RFC 9449 §7.1, RFC 6750 §3.1 |
| User cancels at the authorization endpoint | redirect with `error=access_denied` (and `state`, `iss`) | RFC 6749 §4.1.2.1, RFC 9207 |

Keep ecosystem-specific reasons in `error_description`; do not invent new top-level `error` values where a standard
one fits.

<a id="cf-pkce-missing-verifier"></a>
## Missing `code_verifier`

`fapi2-…-ensure-pkce-code-verifier-required` expects `invalid_grant` (`CheckErrorFromTokenEndpointResponseErrorInvalidGrant`,
`RFC6749-5.2`, `RFC7636-4.6`): the grant cannot be verified without the verifier. Return `400 invalid_grant` and burn the
code. Also validate the verifier syntax (43–128 unreserved characters, RFC 7636 §4.1).

<a id="cf-cache-control"></a>
## `Cache-Control: no-store` on token responses

`CheckTokenEndpointCacheHeaders` (`RFC6749-5.1`): every token endpoint response — success **and** error — must carry
`Cache-Control: no-store`. Set it in one place (middleware for the route), not per success branch. The refresh-token
module checks error responses, which is where it is usually missing.

<a id="cf-refresh-token-binding"></a>
## Refresh token bound to the wrong key

- **Module:** `fapi2-security-profile-final-refresh-token`. With `client_auth_type=client_attestation` it (a) refreshes
  with a **fresh DPoP key** but the same client instance key, (b) tries a **different client instance key** (must fail,
  `OAuth2-ATCA07-10.3`), (c) tries without client authentication (must fail, RFC 6749 §6), (d) tries without DPoP proof.
- **Symptom:** `invalid_grant "refresh token is bound to another DPoP key"` on the first, legitimate refresh.
- **Spec:** RFC 9449 §5 binds refresh tokens to the DPoP key only for *public* clients; ATCA §10.3 binds refresh tokens
  issued to an attested client to the **client instance key** (the `cnf` key of the client attestation). Bind to that key,
  require a valid DPoP proof (any key) for the new access token, and reject a different instance key with
  `invalid_grant` / `invalid_client`. If you rotate refresh tokens, FAPI2 §5.3.2.1 discourages rotation; the suite also
  retries the previous refresh token after 30 s.

<a id="cf-refresh-scope"></a>
## Refresh tokens and companion scopes

- The suite calls the token endpoint with the refresh token **immediately** after the first token response, before any
  credential request. RFC 6749 §6: a refresh token is usable from issuance. If your refresh grant depends on state that is
  only created when a credential is issued, carry it on the authorization until then.
- A refresh request without `scope` yields the original scope (RFC 6749 §6). The refreshed access token must be usable
  for the same credential configurations; if it cannot be (by design), do not issue the refresh token for that scope.
- If you issue refresh tokens only when a specific additional scope is requested, the suite's PAR (which requests only
  the configured credential scope) gets none and the module ends **SKIPPED** ("Refresh tokens cannot be tested"). That is
  a correct outcome, not a failure — document it.

<a id="cf-code-reuse-revocation"></a>
## Authorization code reuse should revoke tokens

`fapi2-…-attempt-reuse-authorization-code-after-one-second`: the second redemption must fail with `invalid_grant`, and the
suite then calls the resource with the first access token. `EnsureHttpStatusCodeIs4xx` as WARNING (`RFC6749-4.1.2`,
`RFC6750-3.1`) means you did not revoke it. RFC 6749 §4.1.2: the server SHOULD revoke all tokens previously issued based
on that code. Mark the code as reused and invalidate its tokens (RFC 9700 discusses code replay mitigations).

<a id="cf-dpop-htu-normalization"></a>
## DPoP `htu` comparison

`fapi2-…-dpop-negative-tests` sends `htu` with an upper-case scheme/host and with the default port `:443`, expecting
acceptance (WARNING on rejection, `RFC3986-6.2.2`, `RFC3986-6.2.3`). RFC 9449 §4.3: compare `htu` to the request URI
ignoring query and fragment, using syntax- and scheme-based normalization. Lower-case scheme and host, drop the default
port, keep the path case-sensitive. The same module also checks the negative cases: missing `typ`/`alg`/`jwk`/`jti`/
`htm`/`htu`/`iat`/`ath`, `alg: none`, RS256 when only ES256 is advertised, private key in `jwk`, wrong `htm`, other URL,
`iat` ±1 h, reused `jti` ("should" fail), wrong `ath`, other key, multiple `DPoP` headers, `Bearer` instead of `DPoP`.

<a id="cf-www-authenticate"></a>
## 401 without `WWW-Authenticate: DPoP`

Credential, nonce-protected and notification endpoints accept DPoP-bound tokens. On a token or proof failure, answer
`401` with `WWW-Authenticate: DPoP error="invalid_token"` (or `"invalid_dpop_proof"`), including `algs="ES256"` (RFC 9449
§7.1; RFC 6750 §3). The authorization scheme is case-insensitive (`fapi2-…-access-token-type-header-case-sensitivity`,
RFC 9110 §11.1): accept `dpop` as well as `DPoP`. If you require server nonces, use `use_dpop_nonce` with a `DPoP-Nonce`
header (RFC 9449 §8, §9); the suite handles that.

<a id="cf-nonce-race"></a>
## `c_nonce` consumption is not atomic

Not a dedicated module, but the suite and real wallets send concurrent requests. Consume the nonce atomically
(compare-and-delete, or a unique constraint) **before** any await, so two credential requests with the same nonce
cannot both succeed (VCI §7, nonce endpoint; replay protection). Don't put a nonce back after a failed proof check.

<a id="cf-browser-steps"></a>
## Browser steps the tester gets wrong

- `fapi2-…-user-rejects-authentication`: press **Cancel/Deny** on the login or consent page (for both clients if the
  test opens the page twice). Approving produces `ExpectAccessDeniedErrorFromAuthorizationEndpointDueToUserRejectingRequest`
  and `EnsureErrorFromAuthorizationEndpointResponse` failures. Clear authorization-server cookies first if a session
  would log you in silently.
- Error-page modules (`…-ensure-unsigned-authorization-request-without-using-par-fails`, `…-par-attempt-reuse-request_uri`,
  `…-par-attempt-to-use-request_uri-for-different-client`, PKCE / response_type modules that end at the authorization
  endpoint): when your server shows an error page, upload a screenshot of it; the module finishes as **REVIEW**. A
  rendered HTML page with a clear "request invalid or expired" message is better than raw JSON for this.

<a id="cf-request-uri-reuse-before-auth"></a>
## `request_uri` reused before authentication completes

`fapi2-…-par-ensure-reused-request-uri-prior-to-auth-completion-succeeds` opens the authorization endpoint twice with the
same `request_uri`. On the **first** visit do nothing (don't log in, don't tick anything, don't close the tab) and go back
to the suite; on the second visit complete the flow. The server must allow the second visit (FAPI2 §5.3.2.2, note 3;
one-time use is enforced when the code is issued, RFC 9126 §7.3). "The user was authenticated on the initial visit to
login page" means the tester logged in too early — re-run.

<a id="cf-expired-request-uri"></a>
## Expired `request_uri`

`fapi2-…-par-attempt-to-use-expired-request_uri` sleeps for the PAR `expires_in` (often 600 s) before using the
`request_uri`. Leave it running in **WAITING**; stopping it gives `WaitForExpiry` "Interrupted while sleeping". Then
upload the error-page screenshot if asked.

<a id="cf-alias-conflict"></a>
## Alias conflicts

"Stopping test due to alias conflict" (INTERRUPTED): you started another test with the same alias before the first one
finished (e.g. while one was waiting for a screenshot). Run exactly one test at a time per alias.

<a id="cf-deploy-during-tests"></a>
## Deploying during a run

`VCIGetDynamicCredentialIssuerMetadata` "Unable to fetch credential issuer metadata" with a `BadGateway` error class (502)
means the service was restarting. Freeze deployments while a plan runs, and re-run the affected modules.

<a id="cf-status-list-fetch"></a>
## Verifier did not fetch the status list

- **Condition:** `EnsureVerifierFetchedRevocationList` — FAILURE in `oid4vp-1final-verifier-present-revoked-credential`,
  WARNING in the happy flows (`SDJWTVC-3.4`, `OTSL-8.3`).
- The suite serves a fresh Token Status List at a new URL under the suite host for every test instance, signed with the
  same key and `x5c` chain as the credential. A verifier that only reads pre-fetched lists can't see it.
- **Fix:** support fetching the referenced status list during verification (with SSRF protection: HTTPS only, host
  allow-list or trust-list-declared endpoint, short timeout, size limit, caching). Accept the list signer the trust
  model allows (here the credential's own signer). `EnsureRevocationListRequestAcceptedServedMediaType` (WARNING) checks
  your `Accept` header accepts `application/statuslist+jwt`. If on-demand fetching is a deliberate test-only switch,
  keep it off by default and scoped to the test policy.
- `…-present-credential-without-status` must be **accepted**: status is optional (TSL), and a credential valid for less
  than 24 h is exempt from revocation in the EU implementing rules the suite quotes.

<a id="cf-ephemeral-encryption-key"></a>
## Response encryption key reused

`VP1FinalCheckEncryptionKeyNotReused` (FAILURE under HAIP, `HAIP-5-6`, `OID4VP-1FINAL-5.1`): the suite remembers the
`client_metadata.jwks` encryption keys it saw and fails if a later request repeats one. Generate a fresh ephemeral
ECDH-ES key per authorization request, include a `kid` (`VP1FinalCheckForKeyIdInClientMetadataJWKs`), and keep the private
key with the transaction only. `ValidateVpClientMetadataEncryptionForHaip` and `VP1FinalValidateClientMetadataJwksForEncryptedResponse`
check the rest (`encrypted_response_enc_values_supported`, key type).

<a id="cf-verifier-policy-for-suite"></a>
## No verifier policy matches what the suite presents

The suite (as mock wallet) presents an EU PID (`vct` `urn:eudi:pid:1`) as `dc+sd-jwt`, or an mdoc for `iso_mdl`.
`CheckDCQLQueryCredentialFormatMatchesTestConfiguration` (FAILURE) fails if your DCQL requests another format. The DCQL
query must request exactly one credential. Create a test-only policy that requests the PID with a couple of claims,
and trust the suite's signing certificate (configured as `credential.signing_jwk` with `x5c`) only in the test
environment. Related WARNINGs: `CheckForNonSelectivelyDisclosableClaimsInDcqlQuery` (don't request `iss`, `vct`, `cnf`,
`status`… as claims, SD-JWT VC §3.2.2.2), `CheckForUnreferencedClaimsInDcqlQuery`, `CheckForUnexpectedParametersInDcqlQuery`.

<a id="cf-request-object-claims"></a>
## Request object claims

`ValidateRequestObjectAudForVP` (WARNING, VP §5.8): `aud` must be `https://self-issued.me/v2` (static discovery) or the
wallet's issuer. `ValidateRequestObjectIat` (WARNING): include `iat` in the payload (a header `iat` does not count).
Others that FAIL: `ValidateRequestObjectTypIsOAuthQauthReqJwt` (`typ: oauth-authz-req+jwt`), `EnsureContentTypeApplicationOauthAuthzReqJwt`
(serve `request_uri` as `application/oauth-authz-req+jwt`), `ValidateRequestObjectSignatureAgainstX5cHeader` and
`ExtractAndValidateX509HashClientId` (`x509_hash:` prefix = base64url SHA-256 of the leaf DER, VP §5.9.3; don't put
the root in `x5c`), `CheckNoRedirectUriInVpAuthorizationRequest` (`direct_post*` uses `response_uri`), `CheckNoScopeParameter`,
`EnsureClientIdMatchesResponseUri` where applicable.

<a id="cf-redirect-uris"></a>
## Redirect URIs for the suite's clients

The suite's callback is `https://<suite-host>/test/a/<alias>/callback`. The second client of the multiple-clients and
FAPI modules uses a **query-suffixed** callback (`…/callback?dummy1=lorem&dummy2=ipsum`) to test exact matching with
queries (RFC 6749 §3.1.2). Register both exactly. If your allow-list is read from an environment file, quote values
containing `&` — a shell-sourced file splits them silently.

<a id="cf-test-only-relaxations"></a>
## Suite-minted attestations lack ecosystem claims

The suite mints client attestations (wallet instance attestations) and key attestations with the claims of the base
specs. Ecosystem rules may require more (a revocation/status reference in the wallet attestation, a key storage claim
in the key attestation, …). If your production policy rejects them:

1. Add an explicit policy switch per claim (e.g. `required | optional`), default **required**.
2. Set it to `optional` only in the test environment that the suite talks to; fail start-up if it is relaxed in
   production.
3. Trust the suite's attestation signer (the `x5c` you put in `client_attestation.attester_jwks` /
   `key_attestation_jwks`) only in that environment's trust configuration.
4. Write the relaxation down next to the results ("deliberate deviation for the self-test").

Never relax the production code path to pass the suite.
