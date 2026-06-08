# Deployment-Linked Sampling Features Clarification (2026-06-08)

| Field | Value |
|---|---|
| **Date** | 2026-06-08 |
| **Author** | Codex |
| **Status** | Clarification Note |
| **Scope** | Distinguishing 1:1 system/deployment modeling from deployment-scoped `samplingFeatures` exposure |
| **Related Reports** | [CSAPI_Deployed_Systems_Design_Pattern](CSAPI_Deployed_Systems_Design_Pattern.md), [CSAPI_Deployment_Modeling_Standards_Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md), [OSH_Sampling_Features_Implementation_Analysis](OSH_Sampling_Features_Implementation_Analysis.md) |

---

## 1  The Question

An external client/plugin question prompted this clarification:

> If a server already models deployed systems using a 1:1 `System`:`Deployment` pattern, does that mean the server is already "attaching features to deployments"?

The answer is **not necessarily**.

Creating a `Deployment` resource for a `System` and exposing `samplingFeatures` from that `Deployment` are related, but they are **not the same thing**.

---

## 2  The Short Answer

There are three distinct facts a server may or may not expose:

1. A `System` exists.
2. A corresponding `Deployment` exists.
3. The `Deployment` exposes a `samplingFeatures` association.

Many publisher patterns implemented so far focus on **(1) and (2)**.

The question being asked by client developers is often about **(3)**:

> Can a client start from the deployment and discover the associated sampling features directly from the deployment side of the resource graph?

That is a separate capability from merely creating a deployment record.

---

## 3  Why the Confusion Happens

The existing OS4CSAPI design work intentionally treats `Deployment` as the operational face of a `System` in many publisher patterns:

- one operationally meaningful system
- one corresponding deployment
- often a 1:1 relationship for user-facing navigation

This is the pattern described in [CSAPI_Deployed_Systems_Design_Pattern](CSAPI_Deployed_Systems_Design_Pattern.md).

However, **a 1:1 deployment pattern does not automatically imply that all system associations are re-exposed from the deployment**.

In other words:

- `System A` may expose `/systems/{id}/samplingFeatures`
- `Deployment A` may exist as the operational wrapper for `System A`
- but `Deployment A` may still fail to expose `/deployments/{id}/samplingFeatures`

The deployment exists, but deployment-scoped discovery is still incomplete.

---

## 4  Standards Basis

OGC API - Connected Systems Part 1 treats `Deployment` as a first-class feature resource with its own associations.

Two standards facts matter here:

### 4.1  Deployments can carry `samplingFeatures`

Part 1 defines `samplingFeatures` as a valid `Deployment` association.

In plain terms, a deployment can expose:

- the systems deployed during the deployment
- the features of interest observed/controlled during the deployment
- the sampling features associated to systems deployed during the deployment

This means Joana's request is **standards-aligned**, not a plugin-specific invention.

### 4.2  Deployment location is not the same thing as sampling features

Part 1 also explicitly distinguishes:

- deployment `location`
- sampling-feature geometry

This distinction is important. A deployment can have a place/time context without that being equivalent to the geometry of the sampling footprint, sensor point, coverage polygon, or observed area.

So "we already have deployment geometry" is **not** the same as "we already publish deployment-linked sampling features."

---

## 5  What the 1:1 Pattern Gives You, and What It Does Not

### 5.1  What it gives you

A 1:1 `System`:`Deployment` pattern can provide:

- operational naming
- valid-time scoping
- deployment hierarchy
- deployment-scoped datastream or observation queries
- continuity of operational role even when hardware changes

These are the strengths already documented in the deployment design reports.

### 5.2  What it does not give you automatically

It does **not** automatically guarantee:

- a `samplingFeatures` link in the deployment representation
- a working `/deployments/{id}/samplingFeatures` traversal
- deployment-scoped aggregation of sampling features across subdeployments
- client discoverability of sampling features when the user navigates from deployments first

Those behaviors must be **explicitly published**.

---

## 6  What a Client Developer Usually Means by "Attach Features Also to Deployments"

When a client developer asks for features "attached to deployments," they usually mean one or more of the following:

1. The deployment representation contains a discoverable `samplingFeatures` association link.
2. The nested route `/deployments/{id}/samplingFeatures` exists and returns useful results.
3. A deployment-centered workflow can retrieve the same relevant feature geometry that is otherwise only discoverable from the system side.

This is mainly a **resource-graph discoverability** request.

It is not necessarily a demand for a different underlying data model.

---

## 7  Practical Interpretation for OS4CSAPI Publishers

If a publisher uses a 1:1 deployment pattern, then deployment-linked sampling features are often a **reasonable next publishing enhancement**, because:

- the system-side association may already exist
- the deployment is already treated as the operational face of the system
- deployment-first client workflows become more complete and intuitive

In many such cases, publishing deployment-linked sampling features is closer to:

- exposing an already meaningful association from another traversal point

than to:

- inventing a wholly new modeling concept

That said, it is still an implementation choice. The Part 1 association is useful and standards-grounded, but it is not the same thing as saying every deployment must always expose it in all publishers.

---

## 8  Recommended Mental Model

Use this distinction:

### A. Modeling layer

> Do we create deployments for deployed systems?

This is the 1:1 deployed-system pattern.

### B. Association layer

> Does a deployment explicitly publish `samplingFeatures` as an associated resource set?

This is the deployment-linked sampling-features question.

### C. Client discoverability layer

> Can a client starting from a deployment discover the relevant feature geometry without having to pivot manually to systems first?

This is usually what plugin authors care about most.

---

## 9  Recommended Response Framing

If asked whether "we already do this," the best accurate response is:

> We often already model deployed systems with a 1:1 `System`:`Deployment` pattern, but that is not automatically the same as publishing deployment-linked `samplingFeatures`. The real question is whether the deployment resource itself exposes a discoverable `samplingFeatures` association or traversal.

That framing preserves the value of the existing deployed-system pattern while correctly identifying the missing capability.

---

## 10  Bottom Line

The likely misunderstanding is:

- **internal assumption:** "we already create deployments, so deployments already have the same feature relationships"
- **client expectation:** "if deployments are first-class operational resources, I should be able to discover sampling features from them directly"

Those are not equivalent.

A server can already be doing good deployment modeling and still have room to improve deployment-scoped sampling-feature discoverability.
