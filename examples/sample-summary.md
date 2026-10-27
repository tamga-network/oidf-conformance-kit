# Conformance log summary

7 test(s): **FAILED** 4, **REVIEW** 1, **SKIPPED** 1, **PASSED** 1

| Result | Module | Variant | Findings |
|---|---|---|---|
| FAILED | `oid4vci-1_0-issuer-metadata-test` | client_attestation sd_jwt_vc vci_haip | 2 |
| FAILED | `fapi2-security-profile-final-happy-flow` | client_attestation sd_jwt_vc vci_haip unsigned plain_oauth dpop wallet_initiated | 2 |
| FAILED | `oid4vci-1_0-issuer-batch-issuance` | client_attestation sd_jwt_vc vci_haip unsigned plain_oauth dpop wallet_initiated plain | 1 |
| SKIPPED | `oid4vci-1_0-issuer-fail-unsupported-encryption-algorithm` | client_attestation sd_jwt_vc vci_haip unsigned plain_oauth dpop wallet_initiated encrypted | 0 |
| REVIEW | `oid4vp-1final-verifier-happy-flow` | x509_hash sd_jwt_vc request_uri_signed direct_post.jwt haip | 3 |
| FAILED | `oid4vp-1final-verifier-present-revoked-credential` | x509_hash sd_jwt_vc request_uri_signed direct_post.jwt haip | 1 |
| PASSED | `oid4vp-1final-verifier-invalid-kb-jwt-nonce` | x509_hash sd_jwt_vc request_uri_signed direct_post.jwt haip | 0 |

## Findings

### `oid4vci-1_0-issuer-metadata-test` — FAILED

- **WARNING** `CheckForUnexpectedParametersInCredentialIssuerMetadata` (OID4VCI-1FINAL-12.2.3): Unknown properties were found in the OID4VCI Credential Issuer metadata.
  - details: unknown_properties=$.credential_configurations_supported.example_pid.credential_metadata.display[0].lang; $.credential_configurations_supported.example_pid.display
  - see `references/common-failures.md#cf-issuer-metadata-unknown-properties`
- **FAILURE** `CheckDiscEndpointClientAttestationSigningAlgValuesSupported` (OAuth2-ATCA07-10.1): attest_jwt_client_auth is supported but required fields are missing
  - details: missing_fields=client_attestation_signing_alg_values_supported; client_attestation_pop_signing_alg_values_supported
  - see `references/common-failures.md#cf-client-attestation-alg-metadata`

### `fapi2-security-profile-final-happy-flow` — FAILED

- **FAILURE** `RequireOnlyBCP195RecommendedCiphersForTLS12` (FAPI2-SP-FINAL-5.2.2, FAPI-ISSUES-847): Server accepted a cipher that is not on the list of permitted ciphers
  - details: cipher_suite=TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA \| port=443
  - see `references/common-failures.md#cf-tls12-ciphers`
- **FAILURE** `VCICheckForDeferredCredentialResponse` (OID4VCI-1FINAL-9): Credential response contains neither credentials nor transaction_id
  - details: credential_response=keys: error; error=invalid_token
  - see `references/common-failures.md#cf-access-token-reuse`
- INTERRUPTED: Test was interrupted before it could complete. The failure 'VCICheckForDeferredCredentialResponse' means the test cannot continue.

### `oid4vci-1_0-issuer-batch-issuance` — FAILED

- **FAILURE** `VCIEnsureBatchTimeClaimsNotLinkable` (SDJWT-10.1): The batch credentials share a precise, high-entropy time claim [iat, exp] which lets verifiers correlate the credentials.
  - details: precise_time_claims=iat; exp \| iat_distinct_values=[1792600765] \| exp_distinct_values=[1855672765]
  - see `references/common-failures.md#cf-time-claims-linkable`

### `oid4vci-1_0-issuer-fail-unsupported-encryption-algorithm` — SKIPPED

- SKIPPED: The test was skipped: Credential encryption is not supported by the credential issuer - neither credential_response_encryption nor credential_request_encryption are present in the credential issuer metadata.

### `oid4vp-1final-verifier-happy-flow` — REVIEW

- **WARNING** `CheckForUnexpectedParametersInVpAuthorizationRequest`: Unknown parameters were found in the authorization request.
  - details: unknown_params=purpose
  - see `references/common-failures.md#cf-purpose-parameter`
- **WARNING** `ValidateDirectPostResponse` (OID4VP-1FINAL-8.2): Direct post response object contains unexpected keys
  - details: response=keys: extra_url, redirect_uri
  - see `references/common-failures.md#cf-unknown-keys-in-responses`
- **REVIEW** `ExpectVerifierSuccessfulVerificationPage` (OID4VP-1FINAL-8.2): Upload a screenshot showing that the verifier successfully verified the presented credential.
  - details: img=<screenshot uploaded>

### `oid4vp-1final-verifier-present-revoked-credential` — FAILED

- **FAILURE** `EnsureVerifierFetchedRevocationList` (SDJWTVC-3.4, OTSL-8.3): The verifier did not fetch the status list the presented credential references, so it cannot have detected the revocation. Contact: <email>
  - see `references/common-failures.md#cf-status-list-fetch`
