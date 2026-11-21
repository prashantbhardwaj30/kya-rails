# KYA spec v0.1 (this project's interpretation)

> **Read this first.** MAS announced on 19 Nov 2026 that it will *facilitate the development* of a Know Your Agent protocol. It named the information the protocol should carry but did **not** publish field names or a schema ([MAS keynote, paras 51–53](https://www.mas.gov.sg/news/speeches/2026/keynote-address-by-md-at-the-singapore-fintech-festival-2026)). Every field below is our own design. Where a field borrows from a published source, the source is linked.

## Sections and where they come from

| Manifest section | MAS KYA information item (keynote para 52) | Other sources it borrows from |
|---|---|---|
| `identity` | (a) who the agent is | Agent key as a JWK ([RFC 8037](https://www.rfc-editor.org/rfc/rfc8037)); `did:web` ids; developer and operator as registered legal entities (CIN, GSTIN, LEI, UEN) |
| `representation` | (a) whom it represents | Experian's "human-to-agent binding" ([Experian Agent Trust](https://www.experian.com/business/products/agent-trust)); masked display name and salted principal hash for DPDP data minimisation ([DPDP Act 2023, s.6](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf)) |
| `authority` | (b) what authority it has been given | SAFR "Authorisation" control category: who may delegate to whom, to what depth, which action types ([SAFR v1.1, Table 1](https://www.mas.gov.sg/-/media/mas-media-library/development/fintech/ai-safr/safr-v1-1.pdf)) |
| `mandate` | (c) what mandate it operates under | SAFR mandate definition: what the agent may do, within what limits, under what conditions; SAFR "Exposure Limits" and "Rate Limits"; UPI Reserve Pay-style block limits ([MIT Sloan Management Review India summary of the NPCI circular](https://mitsloanindia.com/article/indias-agentic-payment-push-leaves-liability-unclear/)) |
| `mandate.consent` | not in MAS list | DPDP Act s.6: consent limited to the specified purpose and the data necessary for it |
| `assurance` | (d) what assurance exists about its provenance and reliability | SAFR "Evidence Quality" category; "controls proportionate to authority" (keynote para 50d) |
| `proof` | not in MAS list | Compact JWS with detached payload ([RFC 7515 Appendix F](https://www.rfc-editor.org/rfc/rfc7515#appendix-F)), EdDSA |

The brief that started this repo listed four pillars (identity, representation, authority, mandate). The MAS keynote lists a fifth, assurance, so it is included.

The **action envelope** (`action.schema.json`) follows the SAFR "governance envelope": the action, the action trace, and context metadata. It is signed by the agent's own key, which proves the agent named in the manifest actually sent it.

## Design rules

- **Strict.** `additionalProperties: false` everywhere. Unknown fields fail validation rather than being ignored.
- **No floats.** Money is integer paise. That keeps canonical JSON identical to RFC 8785 for this data and avoids rounding disputes.
- **No raw identifiers.** `principal_ref` must be a salted SHA-256. A PAN or Aadhaar number fails the pattern.
- **Revocable or rejected.** `authority.revocation.revocable` is `const: true`.
- **Fictional data only.** Organisations, accounts and VPAs in the examples are invented; domains use the reserved `.example` TLD.

## Examples

| Folder | What it holds | Expected result |
|---|---|---|
| `examples/valid/` | Four scenarios: credit bureau check, loan disbursal, UPI-style household payment, WhatsApp payment link | Schema-valid, correctly signed, pass all gates |
| `examples/attacks/` | Injected payee, DPDP purpose misuse, forged issuer | Schema-valid, but must be **denied** by the gates |
| `examples/invalid/` | One broken rule per file, named in the file name | Fail schema validation |

Regenerate everything with `python scripts/build_examples.py`. Keys come from `kya/demo_keys.py`, which derives them from public seeds: demo only.
