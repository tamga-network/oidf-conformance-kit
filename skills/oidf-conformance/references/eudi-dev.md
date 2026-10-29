# Complementing the suite with eudi-dev (ARF checks)

The OpenID Foundation suite tests the protocols: OpenID4VCI, OpenID4VP, HAIP 1.0 and FAPI 2.0. It does **not** check the
EU-specific rules that an EUDI wallet applies on top: access certificates, registration certificates (ETSI TS 119 475),
over-asking (ARF RPRC_21), trusted lists (ETSI TS 119 602) and the signature profile of those lists. A second, independent
counterpart catches a different class of findings.

[eudi-dev](https://github.com/eudi-dev/eudi-dev) is an open-source (Apache-2.0) test wallet for EUDI issuers and verifiers
with a web UI, a CLI and an HTTP API. With `--arf` it checks issuers and verifiers against the ARF; with `--haip` against
HAIP 1.0. It is an independent project: not affiliated with the European Commission or the OpenID Foundation, and a clean
run is not a certification. The notes below were written against v3.5.0 (2026-10-25); the tool moves fast, so check its
[docs](https://github.com/eudi-dev/eudi-dev/tree/main/docs) for your version.

## What it adds to the suite

| Area | eudi-dev checks (with `--arf`) | Suite equivalent |
|---|---|---|
| Verifier request | request object signed with an **access certificate** that chains to a trusted access-CA list (RPA_03/04); CRLs on the path readable and not revoked (RPA_06a) | x509_hash and signature only |
| Registration certificate | one `registration_cert` in `verifier_info` (RPRC_19); signed by a trusted registrar, bound to the access certificate's `organizationIdentifier` (RPRC_17a); every ETSI TS 119 475 Table 7 field present, incl. `policy_id`, `certificate_policy`, `status` | not checked |
| Over-asking | every DCQL query and claim registered in the certificate's `credentials` — by **format + type + path** (RPRC_21) | not checked |
| Issuer metadata | signed metadata with an access certificate (ISSU_22/32); `issuer_info` registration certificate, entitlement and `provides_attestations` (ISSU_24a/b, ISSU_34a/b, RPRC_22a/b/23) | metadata shape only |
| Received credentials | issuer chain to a trusted list for its category, status list readable (ISSU_07–10), HAIP x5c rules | partly |
| Trusted lists | ETSI TS 119 602 lists: parse, JAdES signature, signer chain | not checked |
| Digital Credentials API | answers `navigator.credentials.get()` over its HTTP API or a browser extension | DC API variants only for wallets |

`--mode debug` reports findings and continues; `--mode strict` refuses — run both. **Strict is what a strict EU wallet
will do**: a finding you call "only a warning" in debug mode can be a refusal in production.

## Run it against your test deployment

```bash
# 1. a pinned release binary (or: docker run -p 8085:8085 -p 8086:8086 ghcr.io/eudi-dev/eudi-dev)
curl -fsSL -o eudi https://github.com/eudi-dev/eudi-dev/releases/download/v3.5.0/eudi-v3.5.0-linux-amd64
sha256sum eudi   # compare with checksums.txt of the release
chmod +x eudi

# 2. a wallet that trusts only your test PKI (public certificates only)
./eudi wallet serve --arf --mode debug --auto-accept --no-register --no-open \
  --relying-party-ca test-root.pem --trusted-list-ca test-root.pem -d
./eudi trust add-ca --list registrar --ca test-registrar.pem   # your registration-certificate signer
./eudi trust add-ca --list eaa --ca test-root.pem             # credential issuers of your category
```

- **Verifier:** create a request on your verifier, then `POST /api/presentations` with `{"uri": "openid4vp://…"}`. The
  answer carries `findings`; the activity log (`eudi wallet logs --json`) has them even when no credential matches.
- **Issuer:** `POST /api/offers` with an offer URI. For a wallet-initiated issuer, build a by-value offer
  (`openid-credential-offer://?credential_offer=…` with `grants.authorization_code`); the metadata checks run before PAR.
- **DC API:** `POST /api/dc-api` with `{"digital":{"requests":[…]}}` and an `Origin` header, then post the returned
  `response` to your verifier the way your page would.
- **Trusted lists:** `eudi validate <url-of-list.jws>` and `eudi trust add-list <url>` (signer CA via
  `trust add-ca --list trusted-list-ca`).

### End-to-end presentation

eudi-dev presents credentials signed by its own CA, which your verifier does not trust. To get past "issuer not trusted",
let eudi-dev hold a credential signed by the **mock PID issuer from your suite PKI** ([pki.md](pki.md)), which your test
trust list already accepts:

```bash
./eudi issue sdjwt --wallet --pid --key pid-issuer.key --cert pid-issuer.pem --exp 24h --category unlisted --status-list-uri ""
```

`--status-list-uri ""` leaves out the status entry (eudi-dev's own status list lives on `localhost` and is unreachable
from your server). Treat the key like the suite configuration: test only, never in a public repository.

### Issuance end-to-end

eudi-dev is its own wallet provider: its client attestation is signed by a certificate it generates (not deterministic
across fresh state directories, even with `--seed`). Your issuer accepts it only if that certificate is on your test
wallet-provider list, and eudi-dev v3.5.0 cannot use a wallet-provider key you supply. If your test list only admits test
certificates you issued yourself, PAR fails with your "unknown wallet provider" error — classify it as **expected** and
keep the metadata checks, which run before PAR.

## Typical findings and how to classify them

Use the same classes as for the suite (real bug · config · expected · decision · tool limitation).

| Finding | Usually | Fix |
|---|---|---|
| RPRC_21 over-asking for an **mdoc** or **ZK** request while the claim is registered | real bug | the registration certificate registers each use in its presentation format: `mso_mdoc` + `doctype_value` + `[namespace, element]`, not `dc+sd-jwt` + `vct_values` (TS 119 475 Annex B.2.9) |
| DC API response rejected for missing `state` | real bug (verifier) | OpenID4VP 1.0 Appendix A.2: `state` is not defined for the DC API; do not require it there (keep it on the cross-device path) |
| DC API SD-JWT rejected: KB-JWT `aud` | real bug (wallet and/or verifier) | Appendix A.4: over the DC API the audience is `origin:<origin>`, **also for signed requests**; cross-device keeps the client identifier |
| List signature fails with an unknown critical header `sigT` | real bug (list signer) | ETSI TS 119 182-1 V1.2.1 §5.1.11 / §5.2.1: since 2025-07-15 new JAdES signatures carry the signing time in `iat`, not `sigT`; readers still accept `sigT` |
| `registration_cert` data: plain JWT vs base64url of the JWT | interoperability | ETSI TS 119 472-2 V1.3.1 RO-16 says "base64url encoding of the serialized registration certificate"; implementations differ — wallets should read both |
| Registration certificate has no `policy_id`, `certificate_policy`, `status` | decision | TS 119 475 Table 7 lists them; strict mode refuses. Outside the EU, pick your own policy identifier instead of ETSI's EU OID |
| RPRC_22b "service \"\"" vs access certificate `organizationalUnit` | decision | no TS 119 475 claim for the service identifier; eudi-dev reads `serviceIdentifier` (EC TS5). Align the claim name and put it in issuer certificates too |
| "issuer metadata carries no registration certificate" | warning until 2028-08-11 | add `issuer_info` (TS 119 472-3 §4.2.3) |
| "Attestation catalogue: … has no entry" | tool limitation | eudi-dev's own catalogue; add an entry with `--catalog` if you want type-based checks |
| Query for `urn:eudi:pid:1` "without a domestic PID type" | expected (advice) | list accepted national PID types in `vct_values` if you take them |
| A custom (non-standard) format in DCQL reported as over-asking | expected | non-standard formats have no registered type |

## In CI

Run it weekly and after each release against your test deployment; fail on findings you have not classified.

```yaml
- run: |
    curl -fsSL -o eudi "https://github.com/eudi-dev/eudi-dev/releases/download/${EUDI_VERSION}/eudi-${EUDI_VERSION}-linux-amd64"
    echo "${EUDI_SHA256}  eudi" | sha256sum -c -
    chmod +x eudi
    ./eudi wallet serve --arf --mode debug --auto-accept --no-register --no-open \
      --relying-party-ca test-root.pem --trusted-list-ca test-root.pem -d
- run: node your-checks.mjs   # requests → /api/presentations, offers → /api/offers, compare findings with a known list
```

Gotchas:

- **Do not name your own variables `EUDI_DEV_*`.** Every flag can be set as `EUDI_DEV_<FLAG>`, and `wallet serve` stops on
  an `EUDI_DEV_` variable that is not a flag (for example `EUDI_DEV_VERSION`).
- Pin the version and the SHA-256 of the binary; the tool releases often and its checks change.
- Keep the mock PID key in a CI secret of a private repository; without it, run only the request and metadata checks.
- Only trust a registrar certificate after comparing its fingerprint with your published trusted list, not because it
  arrived in a request.
- The wallet binds `127.0.0.1`; the runner talks to it locally, your deployment over the internet. Never expose it.
