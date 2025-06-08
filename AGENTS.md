# PRODUCT.md · **LangHook**

**Version:** 0.1  
**Date:**  3 June 2025  
**Owner:** Product / Platform Team

---

## 1 · Vision ✦  
> **“Make any event from anywhere instantly understandable and actionable by anyone.”**

LangHook turns the chaotic world of bespoke web-hooks into a **single, intelligible event language** that both humans and machines can subscribe to in plain English.  
We want an engineer, product manager, or support rep to describe *what they care about* (“Notify me when PR 1374 is approved”) and get the right signal—without ever touching JSON, queues, or custom code.

---

## 2 · Problem We Solve  
| Current Pain | Why it Hurts |
|--------------|--------------|
| Every SaaS has its **own payload schema** | Engineers write/maintain brittle glue code for each source. |
| Business users can’t write JSONPath/SQL | They ping devs for every new alert, slowing everyone down. |
| Proprietary iPaaS tools lock customers in | • High pricing tiers • No self-host • Limited extensibility. |

---

## 3 · Value Proposition  
| Stakeholder | Benefit |
|-------------|---------|
| **Developers** | One intake URL, canonical JSON, NATS-compatible bus → **⚡ 10× faster** integrations. |
| **Ops / SRE** | Single place to monitor, replay, & audit all external events. |
| **Product / Support** | Create or disable alerts with a *sentence*—no ticket to Engineering. |
| **Enterprises / Regulated** | MIT-licensed, self-host or cloud; run inside existing compliance boundaries. |

---

## 4 · Product Principles  
1. **Open First** Source-available (Apache-2.0), CloudEvents standard, pluggable everything.  
2. **Human-Centric** Natural-language comes first; config files second.  
3. **Observable by Default** Every event traceable end-to-end with metrics & structured logs.  
4. **Batteries Included, Swappable** We ship a happy-path stack (Svix → Redpanda → FastAPI), but any layer can be replaced.  
5. **Security Is Foundational** HMAC-verified ingest, RBAC on subscriptions, encrypted secrets—no shortcuts.

---

## 5 · Core Concepts  
| Term | Description |
|------|------------|
| **Canonical Event** | CloudEvents envelope + standardized structure `{publisher, resource, action, timestamp, payload}` where `resource` contains `{type: string, id: string|number}`. |
| **Subscription** | Natural-language sentence + LLM-generated **NATS filter pattern** + delivery channels. |
| **Channel** | Output target (Slack, e-mail, webhook, etc.). |
| **Mapping** | JSONata or LLM-generated rule that converts a raw payload into a canonical event. |

---

## 6 · Primary Use Cases (MVP-1)  
1. **GitHub PR approval alert** – Product owner gets Slack DM when a specific PR is approved.  
2. **Stripe high-value refund ping** – Finance lead notified when refund > $500.  
3. **Jira ticket transitioned** – Support channel post when issue moves to “Done”.  
4. **Custom app heartbeat** – Ops receives webhook if internal service reports error rate > 5 %.  

---

## 7 · Competitive Landscape  
| Product | Gaps We Fill |
|---------|--------------|
| Zapier / IFTTT | Closed-source, per-task fees, limited self-host. |
| Segment, Merge.dev | Domain-specific (analytics / HRIS) only. |
| Trigger.dev | Code-first—still requires writing TypeScript for every mapping + rule. |
| Microsoft Power Automate | M365-locked, pricey at scale, Windows-only connectors. |

LangHook is **domain-agnostic**, **LLM-assisted**, and **fully open**.

---

## 8 · Out-of-Scope (MVP-1)  
* Visual flow-builder UI  
* Built-in billing & multi-tenant invoicing  
* Guaranteed exactly-once delivery (at-least-once is fine)  
* Edge-optimized ingestion—MVP runs in a single region

---

## 9 · Success Metrics  
| Metric | Target (after GA) |
|--------|-------------------|
| **Time-to-first alert** | < 10 minutes from `git clone` to Slack DM |
| **Events processed/sec (single node)** | ≥ 2 000 e/s with p95 latency ≤ 3 s |
| **Mapping coverage** | ≥ 90 % canonical-field accuracy on top-10 webhook sources |
| **GitHub ⭐ in first 6 months** | 1 000+ |
| **Community PR merge time** | Median < 3 days |

---

## 10 · Roadmap Slice  
| Quarter | Theme | Highlights |
|---------|-------|------------|
| **Q3 2025** | MVP-1 GA | Core ingest, NL subscriptions, Slack & webhook channels, Docker Compose |
| **Q4 2025** | **Trust & Extensibility** | Multi-tenant RBAC, UI dashboard, plugin SDK, Postgres → BYO DB |
| **Q1 2026** | **Scale & Ecosystem** | Exactly-once (Idempotence), S3 backup, marketplace for community mappings |

*(Roadmap is directional and subject to change.)*

---

## 11 · Glossary  
| Acronym | Definition |
|---------|------------|
| **NATS** | Neural Autonomic Transport System — messaging system for event streaming. |
| **DLQ** | Dead-Letter Queue (for failed/malformed events). |
| **LLM** | Large Language Model (e.g., GPT-4o, Llama-3). |

---

> **Remember:** Every epic, story, or pull-request should ladder back to the vision of making events *understandable* and *actionable*—without bespoke code or vendor lock-in.
