# Verifier plan — `oid4vp-1final-verifier-haip-test-plan`

Display name: **"OpenID for Verifiable Presentations 1.0 Final/HAIP: Test a verifier"** (certifiable). Checked against the
conformance-suite source (`VP1FinalVerifierTestPlanHaip`, master of 2026-10-26).

In this plan the suite is a **mock wallet**. Your verifier creates a request; you paste the `openid4vp://…` link into the
test page (the suite shows an input box, or you replace the `openid4vp://` scheme with the suite's
`authorization_endpoint`); the suite fetches your signed request object, builds a credential signed with
`credential.signing_jwk` and posts the response to your `response_uri`. Each negative module corrupts one thing.

## Variants

| Variant parameter | Choose | Fixed by the plan |
|---|---|---|
| `credential_format` | `sd_jwt_vc` (14 modules) or `iso_mdl` (16 modules) | — |
| `response_mode` | `direct_post.jwt` (`direct_post` is not applicable under HAIP) | — |
| `client_id_prefix` | — | `x509_hash` |
| `request_method` | — | `request_uri_signed` |
| `vp_profile` | — | `haip` |

Configuration: [config-templates/verifier.json](config-templates/verifier.json) — `client.request_object_trust_anchor_pem`
(root of your request-object signing chain) and `credential.signing_jwk` (EC private JWK with `x5c` for the mock issuer;
your verifier must trust that chain in its test environment). For `iso_mdl` also `credential.vical` / `credential.vical_url`
(or an IACA your verifier trusts). See [pki.md](pki.md).

## How results come out

| Your verifier at the `response_uri` | Positive module | Negative module |
|---|---|---|
| `200` + `{"redirect_uri": …}` | suite asks for a screenshot of your success page → **REVIEW** | suite asks for a screenshot of your rejection → **REVIEW** |
| `4xx` | **FAILED** | **PASSED** immediately (`EnsureHttpStatusCodeIs4xx`) |

Rejecting invalid presentations with `400` at the `response_uri` saves screenshots. Don't consume the transaction on a
response that fails holder binding, so a forged post cannot cancel a genuine presentation.

## Checks applied to every module

Request side (before any credential is built): `request_uri` HTTPS, no fragment, fetched with
`Accept: application/oauth-authz-req+jwt` (`EnsureContentTypeApplicationOauthAuthzReqJwt`, `OID4VP-1FINAL-5.10`); `typ`
`oauth-authz-req+jwt`; signature against `x5c` and `client.request_object_trust_anchor_pem`
(`ValidateRequestObjectSignatureAgainstX5cHeader`, `OID4VP-1FINAL-5.9.3`); `x509_hash` client id equals the leaf hash
(`ExtractAndValidateX509HashClientId`); `aud` (`ValidateRequestObjectAudForVP`, VP §5.8), `iat`, `iss` if present, max age;
`response_type=vp_token`; `response_mode`; `response_uri` valid and consistent with the client id; no `redirect_uri`,
no `scope`, no `client_id_scheme`, no `presentation_definition`, no `transaction_data` (unless supported); nonce
characters, length and entropy (`VP1FinalCheckNonceMinimumLength`, `VP1FinalEnsureMinimumNonceEntropy`, VP §5.2); DCQL
valid and requesting exactly one credential of the configured format (`ValidateDCQLQuery`,
`CheckDCQLQueryCredentialFormatMatchesTestConfiguration`, VP §6); `client_metadata` with `vp_formats_supported` for the
requested format, an encryption JWK **with `kid`**, `encrypted_response_enc_values_supported`
(`ValidateVpClientMetadataEncryptionForHaip`, `HAIP-5-5`), and a **fresh** key per request (`VP1FinalCheckEncryptionKeyNotReused`,
`HAIP-5-6`); unknown parameters (`CheckForUnexpectedParametersInVpAuthorizationRequest`, WARNING).

Response side: content type JSON, body `{}` or only `redirect_uri` (`ValidateDirectPostResponse`, WARNING), `redirect_uri`
mandatory under HAIP (`VP1FinalEnsureDirectPostResponseHasRedirectUriForHaip`, `HAIP-5.1`).

Status: for credentials with a `status.status_list` reference the suite serves a Token Status List at a per-instance URL
and records whether you fetched it (`EnsureVerifierFetchedRevocationList`) and with which `Accept`
(`EnsureRevocationListRequestAcceptedServedMediaType`). See [status list fetch](common-failures.md#cf-status-list-fetch).

## Module reference

### 1. `oid4vp-1final-verifier-happy-flow` (positive)
- **Checks:** a valid PID (`vct` `urn:eudi:pid:1` for SD-JWT VC; mDL / Photo ID / EU PID mdoc for `iso_mdl`) with a
  valid status list → accept. VP §8.2, HAIP §5.
- **Typical failures:** no policy requesting the PID ([test policy](common-failures.md#cf-verifier-policy-for-suite));
  suite signer not trusted; status list not fetched (WARNING here); extra keys in the direct_post response.
- **Screenshot:** your success page (show the verified claims) → REVIEW.

### 2. `oid4vp-1final-verifier-minimal-cnf-jwk` (positive)
- **Checks:** `cnf.jwk` with only `kty`, `crv`, `x`, `y` → accept. Don't require `kid`, `alg`, `use` in holder keys.
- **Screenshot:** success → REVIEW.

### 3. `oid4vp-1final-verifier-request-uri-method-post` (positive)
- **Checks:** wallet fetches the request with HTTP POST and `wallet_nonce` (VP §5.10, `EnsureWalletNonceClaimMatchesPostedValue`).
- **Outcome:** **SKIPPED** if your request doesn't carry `request_uri_method=post`. Expected when you only support GET.

### 4. `oid4vp-1final-verifier-request-uri-fetched-twice` (positive)
- **Checks:** the `request_uri` serves the request object again on a second fetch (VP does not make it single-use).
- **Typical failures:** request deleted after first fetch → 404.
- **Screenshot:** success → REVIEW.

### 5. `oid4vp-1final-verifier-invalid-kb-jwt-signature` (negative)
- **Checks:** KB-JWT signature not verifiable with `cnf` → reject (SD-JWT §7.3).

### 6. `oid4vp-1final-verifier-invalid-credential-signature` (negative)
- **Checks:** issuer signature corrupted → reject.

### 7. `oid4vp-1final-verifier-invalid-sd-hash` (negative)
- **Checks:** KB-JWT `sd_hash` doesn't match the presented SD-JWT → reject.

### 8. `oid4vp-1final-verifier-invalid-kb-jwt-nonce` (negative)
- **Checks:** KB-JWT `nonce` ≠ request nonce → reject (VP §14.1 replay).

### 9. `oid4vp-1final-verifier-invalid-kb-jwt-aud` (negative)
- **Checks:** KB-JWT `aud` ≠ your client identifier (including the `x509_hash:` prefix) → reject.
- **Typical failures:** comparing `aud` without the prefix, or against the `response_uri`.

### 10. `oid4vp-1final-verifier-kb-jwt-iat-in-past` (negative)
### 11. `oid4vp-1final-verifier-kb-jwt-iat-in-future` (negative)
- **Checks:** KB-JWT `iat` one year off → reject. Use an acceptance window of minutes, not hours.

### 12. `oid4vp-1final-verifier-present-revoked-credential` (negative)
- **Checks:** credential's status list marks it revoked → reject; the suite fails the module if you never fetched the list.
- **Typical failures:** pre-fetch-only status handling → FAILURE ([fix](common-failures.md#cf-status-list-fetch)); list
  signer (the credential's own `x5c` leaf) not accepted.
- **Outcome:** `4xx` → PASSED; `200` + rejection page → screenshot → REVIEW.

### 13. `oid4vp-1final-verifier-present-credential-without-status` (positive)
- **Checks:** no `status` claim, validity < 24 h → accept (status is optional in SD-JWT VC / TSL; short-lived
  attestations are exempt from revocation in the EU implementing rules the suite cites).
- **Screenshot:** success → REVIEW.

### 14. `oid4vp-1final-verifier-wrong-vct` (negative)
- **Checks:** `vct` not in the DCQL `vct_values` and not inheriting from one → reject (DCQL, VP §6; SD-JWT VC type).
- **Outcome:** usually `200` + "type not accepted" page → screenshot → REVIEW; `4xx` → PASSED.

### 15. `oid4vp-1final-verifier-invalid-session-transcript` (`iso_mdl` only)
- **Checks:** mdoc device authentication computed over an `OpenID4VPHandover` with a wrong nonce → reject
  (ISO/IEC 18013-5 §9.1.3; VP Appendix B.2.6).

### 16. `oid4vp-1final-verifier-present-credential-on-identifier-list` (`iso_mdl` only)
- **Checks:** MSO `status.identifier_list` naming a revoked identifier (ISO/IEC 18013-5 §12.3.6.2) → reject.

## Suggested run order

1 (happy flow) first; fix until it is REVIEW without warnings. Then 2, 4, 13; then the fast negatives 5–11 (they should
all PASS on `4xx`); then 12 and 14; 3 last or not at all. Generate a **new request (QR/link) for every module** —
requests are usually short-lived and single-transaction.

## Typical final picture

No FAILED, no WARNING; REVIEW for the positive modules and any negative module you answer with `200`; SKIPPED for
`request-uri-method-post` if you don't offer POST.
