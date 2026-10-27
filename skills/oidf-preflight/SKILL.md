---
name: oidf-preflight
description: Pre-flight code checklist to run against an OpenID4VCI issuer / OAuth authorization server or an OpenID4VP verifier codebase BEFORE the first OpenID Foundation conformance suite run (HAIP and FAPI 2.0 plans). Inspects metadata, PAR/PKCE/DPoP handling, token and credential endpoint errors, TLS configuration, refresh-token binding, time-claim rounding, verifier request objects, encryption keys and status-list fetching, and writes a pass/risk/unknown report with file references. Use when someone is about to run the conformance suite, asks "are we ready for OIDF / HAIP / FAPI2 tests", or wants to predict conformance failures from code.
---

# OIDF pre-flight checklist

Goal: find the findings the conformance suite will report, from the code, before spending hours in the suite. Each
item lists what to look for, how to search, and what "good" looks like. Details and spec citations for every item are in
[`../oidf-conformance/references/common-failures.md`](../oidf-conformance/references/common-failures.md).

## How to run

1. Identify the components in scope: credential issuer, authorization server (PAR, token), credential/nonce/notification
   endpoints, reverse proxy/TLS config, verifier (request object, `response_uri`, status checking). Note the
   language/framework and where routes are defined.
2. For each item below, search (Grep/Glob for the patterns, adapted to the codebase's naming), read the relevant code,
   and classify: **OK** (evidence it's right), **RISK** (evidence it's wrong or missing — say what the suite will
   report), **UNKNOWN** (can't tell from code; needs a live check), **N/A** (component not in scope).
3. If a running test environment is available, confirm the live items (metadata, TLS, headers) with `curl`/`openssl`.
4. Don't change code in this skill. Produce the report (template at the end) and hand RISK items to the `oidf-fixer`
   agent or the team.

Search tip: patterns are regexes for Grep; widen them with the project's own identifiers once you find the module.

## A. Issuer and authorization server metadata

| # | Check | Look for | Good |
|---|---|---|---|
| A1 | Client attestation alg lists | `attest_jwt_client_auth`, `client_attestation_signing_alg_values_supported`, `client_attestation_pop_signing_alg_values_supported` | Both arrays present, non-empty, wherever `attest_jwt_client_auth` is advertised |
| A2 | AS metadata basics | `pushed_authorization_request_endpoint`, `require_pushed_authorization_requests`, `code_challenge_methods_supported`, `dpop_signing_alg_values_supported`, `authorization_response_iss_parameter_supported` | PAR required, `["S256"]` only, `["ES256"]` (or what you support), iss parameter `true` |
| A3 | Display shape | `display` near `credential_configurations_supported`; `credential_metadata` | `display` and `claims` inside `credential_metadata` (VCI §12.2.4), not on the configuration |
| A4 | Locale vs lang | `"lang"` / `lang:` in issuer-metadata code | `locale` in OpenID4VCI metadata; `lang` only in SD-JWT VC type metadata; tags valid BCP 47, canonical case, one object per language |
| A5 | Format identifiers | `vc\+sd-jwt` | `dc+sd-jwt` everywhere |
| A6 | Nonce endpoint | `nonce_endpoint` | Advertised and implemented (HAIP-4.1-5) |
| A7 | Extensions in metadata | non-standard members in issuer/AS metadata builders | Each extension listed with its source spec, ready for the allow-list |
| A8 | Signed metadata | `application/jwt`, `openidvci-issuer-metadata+jwt` | `Accept: application/jwt` returns a signed JWT with the same content |
| A9 | Scope per configuration | `scope` in configurations | Each configuration the suite uses has a `scope` valid per RFC 6749 §3.3 |

## B. PAR, authorization, PKCE

| # | Check | Look for | Good |
|---|---|---|---|
| B1 | PAR method | PAR route registration (`/par`, `pushed`) | Non-POST → `405` (not a framework 404) |
| B2 | `request_uri` in PAR body | PAR parameter parsing | Rejected with `invalid_request` |
| B3 | Duplicate parameters | form parsing that keeps the last value | Duplicates rejected |
| B4 | `response_type` | PAR validation | Only `code`; others → `unsupported_response_type`/`invalid_request` |
| B5 | PKCE | `code_challenge_method`, `plain`, `S256` | Required; `plain` → `invalid_request`; verifier syntax 43–128 chars |
| B6 | `client_id` at `/authorize` | authorization handler | Must match the PAR client (`request_uri` bound to client) |
| B7 | `request_uri` lifetime and reuse | `expires_in`, request store | Reusable until code issuance, single-use after; expiry enforced |
| B8 | Front channel params | `/authorize` handler | Works with only `client_id` + `request_uri` |
| B9 | Error rendering | `/authorize` error paths | Browser-facing errors render an HTML page (screenshot-friendly) or redirect with `error`, `state`, `iss` |
| B10 | User cancel | consent/login cancel handler | Redirect with `error=access_denied` |
| B11 | Redirect URIs | allow-list config / env parsing | Exact match incl. query; values with `&` survive config loading |

## C. DPoP and client attestation

| # | Check | Look for | Good |
|---|---|---|---|
| C1 | DPoP at PAR | `dpop_jkt`, DPoP verification in PAR handler | Proof verified; thumbprint compared with `dpop_jkt` → `invalid_dpop_proof`; stored with the code |
| C2 | Code ↔ key | token handler | Different key → `invalid_grant`; missing DPoP → error |
| C3 | `htu` comparison | `htu` equality | Normalized (lower-case scheme/host, default port dropped), query/fragment ignored |
| C4 | DPoP proof checks | `jti`, `iat`, `ath`, `typ`, `alg`, `jwk` | All checked; `iat` window tolerates ±10 s; replayed `jti` rejected; private `jwk` rejected; `none`/unsupported alg rejected |
| C5 | Scheme case | `Authorization` parsing | `DPoP`/`dpop` both accepted; `Bearer` with a DPoP-bound token rejected |
| C6 | 401 challenge | credential endpoint error path | `401` + `WWW-Authenticate: DPoP error="…", algs="ES256"` |
| C7 | Client attestation validation | WIA/PoP verification | signature, `exp`, `sub`==client_id, PoP `aud`, PoP key == `cnf.jwk`, `jti` replay; errors `invalid_client`/`use_fresh_attestation` |
| C8 | Ecosystem-only claims | required claims beyond ATCA/VCI (status in WIA, key-storage claims in key attestations) | Policy switch, strict by default, relaxable only in the test environment |

## D. Token endpoint

| # | Check | Look for | Good |
|---|---|---|---|
| D1 | `Cache-Control: no-store` | token route response headers | On success **and** every error |
| D2 | Missing `code_verifier` | token handler | `invalid_grant`, code burnt |
| D3 | Code reuse | code store | Second use `invalid_grant` and tokens from the first use revoked |
| D4 | Code lifetime | code TTL | ≤ 60 s |
| D5 | `client_id` mismatch | body `client_id` vs authenticated client | `invalid_client` |
| D6 | Refresh binding | refresh token storage | Bound to the client instance key (attestation `cnf`), not to the DPoP key; different instance key rejected; no client auth rejected |
| D7 | Refresh timing / scope | refresh grant handler | Usable immediately after issuance; no-scope refresh = original scope, usable for the same credentials; if refresh only for a special scope, the suite will SKIP |
| D8 | Error codes | literal `error:` strings | Only RFC 6749 §5.2 / RFC 9449 / ATCA codes; extra reason in `error_description` |

## E. Credential and nonce endpoints

| # | Check | Look for | Good |
|---|---|---|---|
| E1 | Access token reuse | "used"/"consumed" flags on access tokens | Several credential requests per token within its lifetime (or a recorded decision) |
| E2 | Error codes | credential error responses | `invalid_proof`, `invalid_nonce`, `unknown_credential_configuration`, `unknown_credential_identifier`, `invalid_encryption_parameters`, `credential_request_denied` (VCI §8.3.1.2) |
| E3 | Response members | credential response builder | Only `credentials`, `transaction_id`, `notification_id`, `interval` |
| E4 | Nonce atomicity | `c_nonce` consume | Atomic compare-and-delete before any await; not restored on failure |
| E5 | Access token in query | token extraction | Query/form tokens rejected at the credential endpoint |
| E6 | Unknown parameters | strict request schemas | Unknown parameters ignored (the suite adds random ones) |
| E7 | Batch | `proofs`, batch size | One credential per proof, each bound to its key, distinct keys enforced |
| E8 | Time claims | `iat`, `exp`, `nbf`, mdoc `validityInfo` | Rounded (hour/day) or randomized, consistently for exp; not before the signer's `notBefore` |
| E9 | Status indices | status list allocation | Random, unique per credential, shared lists |
| E10 | Notification | issuance state | Issuance doesn't depend on the notification call |

## F. Transport

| # | Check | Look for | Good |
|---|---|---|---|
| F1 | TLS versions | nginx/Caddy/ingress/LB config (`ssl_protocols`, `minVersion`) | TLS 1.2 + 1.3 only |
| F2 | TLS 1.2 ciphers | `ssl_ciphers`, cipher lists | Only ECDHE + AES-GCM (4 suites); live: `openssl s_client -tls1_2 -cipher ECDHE-ECDSA-AES128-SHA` fails |
| F3 | `Date` header | resource responses | Present |
| F4 | Deploy freeze | CI/CD | A way to pause deploys during a run |

## G. Verifier (OpenID4VP)

| # | Check | Look for | Good |
|---|---|---|---|
| G1 | Request object header/claims | request object builder | `typ: oauth-authz-req+jwt`; payload `aud` (`https://self-issued.me/v2`), `iat`, `exp`, `client_id`, `response_uri`, `response_mode=direct_post.jwt`, `nonce` (≥ 128 bits), `state`, `dcql_query`, `client_metadata`; `x5c` without root |
| G2 | No invented parameters | request builder | No `purpose` or other non-VP members; purpose comes from `verifier_info`/registration data |
| G3 | `x509_hash` client id | client id computation | `x509_hash:` + base64url(SHA-256(leaf DER)) |
| G4 | Request URI serving | `request_uri` handler | `application/oauth-authz-req+jwt`; fetchable twice; optional POST with `wallet_nonce` |
| G5 | Encryption key | `client_metadata.jwks` generation | Fresh ephemeral ECDH-ES key per request, with `kid`; `encrypted_response_enc_values_supported` |
| G6 | `vp_formats_supported` | client metadata | Only formats the DCQL query uses |
| G7 | DCQL | policy definitions | One credential per request for the test policy; no non-disclosable claims requested; `vct_values` exact |
| G8 | Response endpoint | `response_uri` handler | Invalid presentation → `400` (no screenshot needed); success → `200 {"redirect_uri": …}` only; transaction not consumed by a failed holder binding |
| G9 | KB-JWT checks | key binding verification | signature vs `cnf`, `nonce`, `aud` (with prefix), `iat` window (minutes), `sd_hash` |
| G10 | Status | status list handling | Fetch at verification time (SSRF-safe), accept list signed by the credential signer when the trust model allows, `Accept: application/statuslist+jwt`; credential without status accepted |
| G11 | Holder key | `cnf.jwk` parsing | Minimal JWK (`kty`, `crv`, `x`, `y`) accepted |
| G12 | Wallet error | `response_uri` handler | Accepts `error`/`state` from a wallet that declines |

## Report template

```markdown
# OIDF pre-flight report — <component> (<commit>)

Scope: <issuer | AS | verifier>, plan(s): <...>, date: <...>

| # | Item | Status | Evidence (file:line) | Expected suite finding if not fixed | Suggested fix |
|---|---|---|---|---|---|
| A1 | Client attestation alg lists | RISK | src/metadata.ts:42 | CheckDiscEndpointClientAttestationSigningAlgValuesSupported FAILURE (metadata, discovery) | add both arrays |

Summary: <n> OK · <n> RISK · <n> UNKNOWN · <n> N/A
Live checks still needed: <list>
Test-only relaxations required for the suite: <list, each with switch name and default>
```
