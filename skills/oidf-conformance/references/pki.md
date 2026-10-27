# Test PKI for the conformance suite (openssl)

The suite needs private keys it can sign with (it plays the wallet or the issuer) and certificate chains your service
trusts **in its test environment only**. Generate a dedicated test root; never reuse production keys, never add this
root to production trust stores. Everything below is EC P-256 / ES256 (HAIP baseline).

```
Self-test Root CA (TEST)                      ← your test trust store / trust list only
 ├── Self-test Wallet Provider (TEST)         ← client_attestation.attester_jwks (+ key_attestation_jwks)
 └── Self-test PID Issuer (TEST)              ← verifier plan: credential.signing_jwk
```

Your own service keeps its normal (test-environment) chain: the issuer's credential signer under the root you put in
`credential.trust_anchor_pem`; the verifier's request-object signer under `client.request_object_trust_anchor_pem`.

## 1. Root

```bash
mkdir -p selftest-pki && cd selftest-pki
openssl ecparam -name prime256v1 -genkey -noout -out root.key
openssl req -new -key root.key -out root.csr \
  -subj "/C=XX/O=Example Self-test (TEST)/CN=Self-test Root CA (TEST)"
printf 'basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n' > root.ext
openssl x509 -req -in root.csr -signkey root.key -days 730 -sha256 -extfile root.ext -out root.pem
```

(Self-signing through `x509 -req` with an extension file avoids `req -x509 -addext`, which on OpenSSL 1.1.1 duplicates
the default `v3_ca` extensions and yields a root that `openssl verify` rejects.) On Git Bash for Windows, run
`export MSYS_NO_PATHCONV=1` first so `-subj "/C=…"` is not rewritten into a Windows path.

## 2. Leaves

```bash
leaf () {  # leaf <name> <CN> [extra -addext ...]
  name=$1; cn=$2; shift 2
  openssl ecparam -name prime256v1 -genkey -noout -out "$name.key"
  openssl req -new -key "$name.key" -subj "/C=XX/O=Example Self-test (TEST)/CN=$cn" -out "$name.csr"
  printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid\n%s\n' "$*" > "$name.ext"
  openssl x509 -req -in "$name.csr" -CA root.pem -CAkey root.key -CAcreateserial \
    -days 365 -sha256 -extfile "$name.ext" -out "$name.pem"
}

leaf attester "Self-test Wallet Provider (TEST)"
# Mock PID issuer for the verifier plan. Add the suite host as SAN if your verifier matches iss to the SAN:
leaf pid "Self-test PID Issuer (TEST)" "subjectAltName=DNS:demo.certification.openid.net"
```

Use `localhost.emobix.co.uk` (or your own host) instead of `demo.certification.openid.net` when you run the suite locally.

Check:

```bash
openssl verify -CAfile root.pem attester.pem pid.pem
openssl x509 -in pid.pem -noout -text | grep -A1 "Subject Alternative Name"
```

## 3. Convert to JWK with `x5c`

`x5c` holds base64 (not base64url) DER, **leaf first, without the root**. `x`, `y`, `d` are base64url without padding.
Requires `pip install cryptography`.

```python
# pem_to_jwk.py <key.pem> <cert.pem> <kid>
import base64, json, sys
from cryptography.hazmat.primitives import serialization
from cryptography import x509

b64u = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
key = serialization.load_pem_private_key(open(sys.argv[1], "rb").read(), None)
cert = x509.load_pem_x509_certificate(open(sys.argv[2], "rb").read())
n = key.private_numbers(); pub = n.public_numbers
jwk = {
    "kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": sys.argv[3],
    "x": b64u(pub.x.to_bytes(32, "big")), "y": b64u(pub.y.to_bytes(32, "big")),
    "d": b64u(n.private_value.to_bytes(32, "big")),
    "x5c": [base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()],
}
assert cert.public_key().public_numbers() == pub, "certificate does not match key"
print(json.dumps(jwk, indent=2))
```

```bash
python pem_to_jwk.py attester.key attester.pem selftest-attester > attester.jwk.json
python pem_to_jwk.py pid.key pid.pem selftest-pid-issuer > pid.jwk.json
```

Put `attester.jwk.json` into `client_attestation.attester_jwks.keys[0]` (and, if you don't make a separate key,
`key_attestation_jwks.keys[0]`), `pid.jwk.json` into `credential.signing_jwk`, and the PEM roots (with `\n` escapes) into
the `*_pem` fields. Keep a copy of the config **without** `d` values next to your results for reference.

## 4. Trust them on your side (test environment only)

- **Issuer / AS:** add `root.pem` (or the attester leaf) as a trusted wallet provider for client attestations and key
  attestations; map `client_attestation.issuer` to it.
- **Verifier:** add `root.pem` (or the PID leaf) as a trusted PID issuer, and accept the same signer for its status list
  tokens (the suite signs status lists with the credential key).
- Prefer a separate test trust list or configuration file that production never loads, and assert at start-up that the
  test root is absent in production.

## 5. Hygiene

- Private keys stay outside the repository; add `*.key`, filled-in configs and exported logs to `.gitignore`.
- Rotate the test PKI if a filled-in config or a raw log was shared.
- Certificates expire: note the `notAfter` dates next to your results.
