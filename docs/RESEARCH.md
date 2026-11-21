# Research notes

Collected on 21 Nov 2026 (IST) before any code was written. Each entry says what the source actually states, so the README's claims can be checked line by line.

## 1. MAS Know Your Agent (KYA) protocol

- **Source:** [MAS MD keynote at SFF 2026, 19 Nov 2026](https://www.mas.gov.sg/news/speeches/2026/keynote-address-by-md-at-the-singapore-fintech-festival-2026), paras 46–53.
- **What it says:** Agents moving into financial activity need authority, accountability and control (para 46). Users handing agents their login credentials is inadvisable (para 47). Three challenges: the FI cannot tell whether the agent has the customer's full authorisation, whether it is within its mandate, or who bears responsibility (para 48). SAFR phase 1 lessons: bounded autonomy; identity and authority clearly established; clear, specific mandates (actions, limits, conditions); controls proportionate to authority (para 50). In the new phase of SAFR, MAS will **facilitate the development** of a KYA protocol carrying (a) who the agent is and whom it represents, (b) what authority it has, (c) what mandate it operates under, (d) what assurance exists about its provenance and reliability (paras 51–52). FIs can then set terms and a dedicated secure channel (para 53).
- **Not published:** field names, a schema, a timeline. Coverage: [Business Times](https://www.businesstimes.com.sg/companies-markets/mas-develop-know-your-agent-protocol-customer-agents-and-financial-institutions), [Straits Times](https://www.straitstimes.com/business/dont-give-ai-agents-your-financial-accounts-login-details-warns-mas-chief-chia-der-jiun).
- **Used for:** the five manifest sections. All field names are this project's interpretation.

## 2. Agentic Money Sandbox (Singapore)

- **Source:** [MAS and FFI media release, 18 Nov 2026](https://www.mas.gov.sg/news/media-releases/2026/mas-and-future-of-finance-institute-set-out-initiatives-in-support-of-national-ai-missions); keynote paras 54–57.
- **What it says:** FFI will establish an Agentic Money Sandbox, a controlled environment to test how AI agents transact with digital money within defined authority, limits and safeguards. Initial use cases are agent-initiated payments and treasury management. In the payments use case, banks and PSPs verify the agent's identity and authority and apply risk controls before executing.
- **Also:** [DPM Gan's speech](https://www.pmo.gov.sg/newsroom/dpm-gan-kim-yong-at-singapore-fintech-festival-2026/) on agents and purpose-bound money; [Fintech Singapore](https://fintechnews.sg/141547/payments/singapore-ai-agent-payments-trials/).
- **Used for:** context only. There is no public interface to build against.

## 3. SAFR (Safeguards for Agentic Finance at Runtime)

- **Source:** [SAFR v1.1 PDF](https://www.mas.gov.sg/-/media/mas-media-library/development/fintech/ai-safr/safr-v1-1.pdf); [publication page, 3 Jul 2026](https://www.mas.gov.sg/publications/monographs-or-information-paper/2026/safeguards-for-agentic-finance-at-runtime).
- **What it says:** A governance checkpoint between an agent's decision and its execution, with four components: Agent Identity, Controls Repository, Disposition Engine, Audit Log. A Governance Envelope carries the action, the action trace, and context metadata, and should not be treated as self-verifying. Identity failure is rejected immediately and logged. A mandate records what the agent may do, within what limits, under what conditions; an agent cannot extend a mandate through its own reasoning. Four outcomes: **Deny, Escalate, Auto-Execute, Observe**. Control categories include Authorisation (who may delegate to whom, to what depth), Exposure Limits, Rate Limits (including against prompt-injected runaway agents) and Evidence Quality. The audit log is tamper-evident and append-only, recording the envelope, the mandate, the outcome, the rules applied and the timing. SAFR is not regulatory guidance. Reference code is **available on request**.
- **Used for:** the disposition mapping, the action envelope, identity short-circuit, the evidence record fields, burst detection.

## 4. Experian Agent Trust

- **Sources:** [product page](https://www.experian.com/business/products/agent-trust); [launch post, 30 Apr 2026](https://www.experian.com/blogs/news/2026/04/30/experian-agent-trust/); [AI agent identity verification](https://www.experian.com/blogs/insights/ai-agent-identity-verification/); [What is KYA](https://www.experian.com/blogs/insights/what-is-know-your-agent-kya/).
- **What it says:** A KYA framework for agentic commerce: verify identity and payment method, bind human to agent (consumer, device, agent), validate intent and risk over time, issue an Agent Trust Token, keep an Agent Registry with dynamic trust scores. Three dimensions: identity, authorisation, intent. Skyfire's KYA identity powers part of the ecosystem ([Skyfire](https://skyfire.xyz/akamai-joins-the-experian-agent-trust-ecosystem-powered-by-skyfire-kya-identity/)).
- **Difference from the brief:** positioned for commerce and fraud, not credit underwriting specifically.
- **Used for:** the `representation.binding` idea and the "intent within scope" checks (RK-006, RK-007).

## 5. NPCI AiNxt and AtOM

- **Sources:** [NPCI press release, 9 Sep 2026](https://www.npci.org.in/uploads/NPCI_Press_Release_NPCI_launches_Agentic_AI_platforms_to_streamline_workflows_accelerate_innovation_and_improve_productivity_at_GFF_2026_8656452db4.pdf); [AtOM site](https://www.npci.org.in/ATOM/ATOM.html); [Setu on AtOM](https://setu.co/blog/inside-npcis-atom-agentic-orchestration-for-upis-coordination-problem); [CNBC TV18](https://www.cnbctv18.com/personal-finance/gff-npci-launches-two-new-agentic-ai-platforms-how-ainxt-atom-will-work-19987594.htm).
- **What they are:** AiNxt is an open-source, enterprise agentic-AI suite (AiNxt OS, Code, CLI, Enterprise) for building and deploying agents. AtOM is an agent-to-agent change-orchestration platform for UPI feature rollouts across NPCI, banks and PSPs, built on JSON-RPC 2.0 and Google's A2A, with a JWT scheme and HMAC signer mirrored between the authority and partner codebases, and digitally signed, auditable interactions.
- **Difference from the brief:** **neither is a payment rail.** The payments-side agent protocol is the Unified Agentic Protocol (see 7).
- **Used for:** `adapters/atom_a2a.py` wraps evidence as a signed JSON-RPC message, the role AtOM's wire plays for change certification.

## 6. Razorpay and Meta Business Agent

- **Sources:** [Razorpay newsroom, 17 Nov 2026](https://razorpay.com/newsroom/razorpay-goes-live-on-meta-business-agent-enabling-payments-inside-whatsapp-business-app/); [Razorpay blog](https://razorpay.com/blog/razorpay-meta-business-agent-whatsapp-payments/); [Meta Business Agent docs](https://developers.facebook.com/documentation/meta-business-agent/overview); [Razorpay Create Payment Link API](https://razorpay.com/docs/api/payments/payment-links/create-standard/).
- **What they say:** Meta Business Agent answers questions and recommends products on WhatsApp; when the customer decides, it generates a Razorpay payment link in the chat (UPI, cards, netbanking). Owners decide when the agent is active, can step into any chat, and can route queries to a person. Meta's eligibility rules exclude Finance, Government, Health, Alcohol, Gambling, OTC drugs and matrimony verticals.
- **Used for:** `adapters/whatsapp_razorpay.py` (payment-link body mirrors the public API shape; financial MCCs refused; escalations hand off to the owner).

## 7. India agentic payments status

- [Business Standard, 12 Sep 2026](https://www.business-standard.com/finance/news/upi-s-ai-protocol-temporarily-on-hold-as-npci-builds-safeguards-126091101413_1.html): NPCI's Unified Agentic Protocol (UAP) put on hold pending RBI clearance; designed so agents can be registered, verified and authorised across UPI without changing the rails. Mentions Pine Labs P3P, Visa TAP, Mastercard Agent Pay Acceptance Framework, AP2 and NPCI's RuPay Agentic Protocol.
- [MIT Sloan Management Review India, 23 Sep 2026](https://mitsloanindia.com/article/indias-agentic-payment-push-leaves-liability-unclear/): Reuters-reported agent registry as part of UAP; UPI Circle full delegation (₹5,000 per transaction, ₹15,000 a month); UPI Reserve Pay (block up to ₹10,000 for a merchant for up to 90 days, debits should follow a customer purchase action); RBI e-mandate framework; NPCI chairman's "AI may recommend, but authentication and final settlement must follow deterministic, auditable rules"; RBI DG Murmu on accountability; "agents will look statistically abnormal by design".
- [Razorpay, NPCI and OpenAI pilot](https://razorpay.com/newsroom/razorpay-npci-and-openai-come-together-to-launch-agentic-payments-ushering-in-ai-driven-commerce-at-national-scale/) and [TechCrunch, 9 Oct 2025](https://techcrunch.com/2025/10/09/india-pilots-ai-chatbot-led-e-commerce-with-chatgpt-gemini-claude-in-the-mix/): ChatGPT checkout pilot over UPI, using UPI Reserve Pay.
- The NPCI Reserve Pay circular itself ([OC 228](https://www.npci.org.in/uploads/UPI_OC_No_228_FY_2025_26_Enhancement_in_UPI_Single_Block_Multiple_Debits_UPI_Reserve_Pay_a9095c181d.pdf)) could not be downloaded from this environment (NPCI blocks scripted fetches), so its limits are cited through MIT SMR India's summary.

## 8. India vs Singapore

- [MediaNama, 11 Sep 2026](https://www.medianama.com/2026/09/223-singapore-safr-agentic-ai-payments-india-gff/): "India has the position. Singapore has the document." SAFR is voluntary; MAS AI Risk Management Guidelines (consulted Nov 2025) will reach agentic AI; India has FREE-AI and draft model-risk guidance; CERT-In proposed human-in-the-loop above financial thresholds; open question on agent payments across the UPI–PayNow link.

## 9. DPDP Act and RBI

- [DPDP Act, 2023](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf), s.6: consent must be free, specific, informed, unconditional and unambiguous, and limited to the personal data necessary for the specified purpose. s.8: fiduciary obligations including erasure when the purpose is no longer served.
- [DPDP Rules, 2025 (MeitY)](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025.pdf): consent managers registered under Rule 4.
- [RBI FREE-AI Committee Report, 13 Aug 2025](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?ID=1306): 7 principles, 26 recommendations; non-binding. No RBI rule specific to AI-agent identity or payments was found as of Nov 2026.
- **Used for:** MD-009 to MD-011 and the schema's ban on raw identifiers.

## 10. Existing agent-identity and agent-payment work

| Project | Type | Notes |
|---|---|---|
| [AP2](https://ap2-protocol.org/) · [repo](https://github.com/google-agentic-commerce/AP2) | Open protocol | Checkout and payment mandates as verifiable digital credentials; v0.2 donated to FIDO; UPI/PIX on the roadmap |
| [Visa Trusted Agent Protocol](https://github.com/visa/trusted-agent-protocol) · [spec](https://developer.visa.com/docs/trusted-agent-protocol/trusted-agent-protocol-specifications) | Open protocol | RFC 9421 / Web Bot Auth signatures for agent identity and intent at merchants |
| [Mastercard Agent Pay](https://www.mastercard.com/us/en/news-and-trends/stories/2025/agentic-commerce-framework.html) | Network framework | Agent registration, agentic tokens |
| [Skyfire KYAPay](https://kyapay.org/specifications/kya-claims) | Open token spec | `kya+jwt` with `aid` (agent) and `hid` (human) claims; [A2A extension](https://github.com/skyfire-xyz/kyapay_a2a) |
| [Trulioo KYA](https://www.trulioo.com/products/kya-verification) | Commercial | Digital Agent Passport: signed, time-bound JWT after developer KYB/AML checks |
| [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) | Transport auth | OAuth 2.1 for HTTP transports |
| [A2A spec](https://a2a-protocol.org/latest/specification/) | Agent metadata | Agent Cards may carry JWS signatures |

## 11. GitHub search log (unauthenticated API, 21 Nov 2026)

| Query (`/search/repositories`) | Total | Relevant hits |
|---|---|---|
| `know your agent` | 1,015 | none relevant in top results (memory/assistant tools) |
| `kya agent` | 127 | open-kya/kya-standard (7★), veldtlabs/veldt-kya (3★), rudycelekli/kya-evidence (3★), skyfire-xyz/kyapay_a2a (3★) |
| `agent identity payments` | 288 | GetBindu/Bindu (identity + payments layer, crypto-oriented), affinidi-ai/agent-gateway |
| `agentic payments mandate` | 222 | Adwaith-R-Nair/Praman (15★), PxA-Labs/Mandate, iamonuwa/kanon (x402 vectors) |
| `AP2 mandate` | 84 | conformance suites and verifiers for AP2 |
| `agent passport` | 646 | agent-passport-system/agent-passport-system (67★) |
| `SAFR agentic` | 11 | cdrc1103/agentic-runtime-governance (unofficial SAFR reference), mdjmay/safr-agent |
| `UPI agent payments` | 116 | payment recovery and reconciliation agents; RuphakVarmaa/pramaan (Razorpay delegation evidence); Chirag8405/fiat402 |
| `credit bureau agent mandate` | 0 | — |
| `agent mandate DPDP` | 0 | — |
| `KYA UPI` | 3 | none relevant |

### Nearest neighbours, inspected

| Repo | Created | Language | Overlap | Difference |
|---|---|---|---|---|
| [Adwaith-R-Nair/Praman](https://github.com/Adwaith-R-Nair/Praman) | 27 Aug 2026 | TypeScript | Signed mandates, deterministic policy, hash-chained ledger, prompt-injection case, started on Razorpay | Shopping on PayPal/Razorpay; no credit lifecycle, no DPDP purpose rules, no MAS KYA structure, no issuer remit or assurance tiers |
| [cdrc1103/agentic-runtime-governance](https://github.com/cdrc1103/agentic-runtime-governance) | 13 Oct 2026 | Python | SAFR outcomes, tamper-evident audit, EdDSA tokens | Generic "Example Bank"; no KYA manifest schema, no India rails or DPDP |
| [RuphakVarmaa/pramaan](https://github.com/RuphakVarmaa/pramaan) | 4 Sep 2026 | TypeScript | Proof-of-delegation and dispute evidence for Razorpay agent payments | Evidence capture only; no gates or schema |
| [agent-passport-system](https://github.com/agent-passport-system/agent-passport-system) | 18 Feb 2026 | TypeScript | Identity, scoped delegation, enforcement, signed receipts | General purpose, not BFSI or India |
| [veldtlabs/veldt-kya](https://github.com/veldtlabs/veldt-kya) | 21 May 2026 | Python | Runtime control, revocation, tamper-evident logs | General purpose |
| [open-kya/kya-standard](https://github.com/open-kya/kya-standard) | 24 Jan 2026 | HTML | KYA disclosure standard | Document, decentralised/solvency focus |

**Conclusion:** the primitives are well covered. Nobody combines the MAS KYA items, Indian credit-lifecycle actions, DPDP purpose limitation as gate rules, and UPI and WhatsApp-commerce constraints in one tested, schema-first reference. That is the gap this repo targets, and the README says so without claiming novelty for the primitives.
