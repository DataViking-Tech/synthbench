# Traitprint Local — P1 Sign-off

**Author:** crew/cpo
**Date:** 2026-04-19
**Decision:** ✅ **APPROVE WITH CONDITIONS**
**Audience:** mayor, founder (WJ), Traitprint eng lead

---

## TL;DR

Approve. This is one of the highest-leverage moves on the board right now —
it's the right product strategy, the right brand signal, and it directly
disarms the single hardest question the AE Miami audience will ask
(*"why does this need a cloud?"*). But the demo risk is real and the
timeline is tight. If the local package can't cleanly ship by Monday
EOD, **announce the initiative publicly at the summit and ship
publicly in Q2** rather than forcing a broken live demo.

---

## Q1. Dilute or strengthen the cloud product?

**Strengthen — decisively.**

The local package is *input-capture*; the cloud is *distribution +
network effects*. They are complements, not substitutes.

- **Local-only jobs** (private, individual, zero-network): build and
  curate your skill vault, tailor a résumé for a JD in Claude, rehearse
  STAR stories, never show it to anyone. Nobody pays for these today
  and nobody will tomorrow — giving them away costs ~nothing.
- **Cloud-required jobs** (network effects): `traitprint.com/<handle>`
  public URL, always-on digital-twin chat hit by recruiters, two-sided
  matching graph, cross-profile search. None of these can exist locally.

Precedent: Obsidian → Obsidian Publish, Tailscale net → Tailscale
control plane, Logseq → Logseq Sync, 1Password vault → sync tier. All
show the pattern: free local-first + paid cloud with
network-effect-only features is a conversion engine, not cannibalization.

The conversion logic is stronger here than in any of the above because
the local user's *reason to upgrade is exogenous and predictable* —
they're going job hunting, getting recruited, or starting to consult.
At that moment the local-to-cloud push is the obvious next step, and
their local vault is already clean because they've been curating it.

**Indirect strengthen:** every user who pushes a vault to cloud has
higher-quality data than a from-scratch cloud signup. Ground truth
for the recommender improves as a byproduct.

Only real cannibalization risk: if cloud pricing is ever set on features
that are *equivalent* to the local offering. Pricing policy must track
cloud-unique value (public URL, twin chat, matching) — never "more
vault slots" or "advanced editor". Document this explicitly in the
pricing guidelines.

---

## Q2. Same package or separate?

**Single `pip install traitprint`, MIT, with `[cloud]` extras group.**

Rationale:
1. **Single search term.** Users will type `pip install traitprint`.
   If that returns "did you mean traitprint-local?" you've lost them.
2. **One brand, one URL, one CLI surface.** `traitprint init` and
   `traitprint push` in the same binary is the cleanest mental model.
3. **Precedent in the portfolio.** SynthPanel is a single package with
   MCP server + CLI + library built in. Consistency.
4. **License clarity.** Entire package MIT — the cloud *service* is
   the paid product, the client is free. Same model as `openai` SDK
   or `stripe-python`.
5. **Optional heavy deps stay optional.** `traitprint[cloud]` pulls in
   anything large (auth, telemetry, sync engine). Core local install
   stays fast.

Reject `traitprint-local` + `traitprint` split — it creates a "lite
vs real" impression that undercuts the local product, forces a naming
decision later when the cloud client itself grows, and leaves the
namespace open for squatters.

---

## Q3. Open-sourcing vault schema + MCP tools — competitor-copy risk?

**Low risk. Higher upside than downside.**

The schema for skill + STAR-story data is **not the moat**. Any
competent engineer can design one in a weekend. If the schema *were*
the moat, Traitprint would already be in trouble.

Real moats:
- Cloud-side data accumulation (only exists if users push).
- Public URLs with handle network effects (`traitprint.com/<handle>`).
- Two-sided matching graph (recruiter-side queries + candidate-side vaults).
- Brand, integrations, distribution.

None of these are exposed by open-sourcing the schema.

**Upside of open-sourcing:**
- Positions Traitprint's schema as *the standard* rather than "a
  proprietary format" — an explicit advantage over LinkedIn's black box.
- Third parties can write importers (LinkedIn → Traitprint, GitHub →
  Traitprint, BambooHR → Traitprint) — every new importer routes users
  into the Traitprint ecosystem.
- Claude Code / ChatGPT / Cursor can build Traitprint-aware features
  against a public spec without Traitprint-specific partnership. Free
  distribution.
- Academic credibility — a public, versioned schema is citable.

**Real risks and mitigations:**
- *Competitor forks local package with their own cloud back-end*
  (e.g., LinkedIn ships a "MyVault" compatible with Traitprint-Local).
  → Low probability (incumbents don't open-source-fork niche tools).
  → Mitigation: **register "Traitprint" as a trademark before launch**
  so any fork must rebrand; keep cloud API versioned and require a
  signed API key with tracked provenance; make `traitprint push` emit
  a cryptographic proof tied to the traitprint.com service origin.
- *Schema drift between local and cloud.* → Ship a schema version
  number in the vault file; cloud accepts or migrates on push.
  Version-skew policy documented in `docs/schema-versioning.md`.
- *MCP tool names squatted by a lookalike server.* → Low risk; MCP
  Registry listing (Tier S from prior memo) establishes the canonical
  `traitprint/*` tool namespace.

---

## Q4. Does the demo flow work?

**Yes — if pre-configured on the demo laptop. No — if done as live
setup.**

The dangerous version:
1. `pip install traitprint` on conference wifi → 30s best case, failure
   modes include PyPI latency, corporate proxies on demo wifi,
   transient dep-resolution issues. **Don't do this live.**
2. `traitprint mcp-serve` then edit `claude_desktop_config.json` and
   restart Claude Desktop → 2-4 minutes of on-stage JSON editing and
   an app restart. **Don't do this live.**
3. On a reboot-heavy laptop, Claude Desktop MCP registration can fail
   silently and the audience just sees "nothing happened". Demo dies.

The safe version:
1. **Pre-install on the demo laptop.** Pre-configured vault already
   contains WJ's imported résumé. Claude Desktop (or Claude Code) is
   already wired to the local MCP server.
2. Show the value-moment first: Claude asks a structured question,
   gets a STAR story back from the local vault, renders it. *"Notice:
   the laptop is in airplane mode. This is entirely local."* (Turn
   wifi off for effect.)
3. Then walk through setup *as narration over slides*, with the
   commands in a code block: `pip install traitprint`,
   `traitprint init`, `traitprint import-resume ./resume.pdf`,
   `claude mcp add traitprint -- traitprint mcp-serve`. The last
   command matters — use Claude Code's `claude mcp add` over Claude
   Desktop JSON editing wherever possible.
4. Close by pushing to cloud: `traitprint push` → refresh
   `traitprint.com/wesley-johnson` → public profile updated live.
   *"This is the upgrade path. Your data, your choice, your moment."*

**Critical pre-Tuesday checks:**
- [ ] `claude mcp add traitprint -- traitprint mcp-serve` works
      end-to-end on a fresh machine.
- [ ] `traitprint mcp-serve` exposes at least 3 tools worth demoing
      (e.g., `vault_search`, `get_story`, `list_skills`).
- [ ] `traitprint push` round-trips to a staging cloud endpoint and
      you can refresh the public profile URL in ≤ 2 seconds.
- [ ] Airplane-mode demo works with no degraded messages.
- [ ] Fallback: pre-recorded screencast of the full flow, ready to
      cut to if anything dies on stage.

---

## Q5. Overall decision

### ✅ APPROVE WITH CONDITIONS

**Conditions (all must hold before public launch):**

1. **Single `pip install traitprint` package, MIT license, `[cloud]`
   extras group for heavy deps.** Not `traitprint-local`.
2. **Register "Traitprint" trademark** before the public-launch blog
   post ships. Cheap, protects against fork-rebrands.
3. **Pricing policy locked:** cloud prices are set on cloud-unique
   features only (public URL, twin chat, matching). Never on features
   that have a local equivalent.
4. **Privacy copy is surgical.** README + CLI `--help` make explicit
   (a) what stays local, (b) exactly what `traitprint push` uploads
   and under what ToS, (c) that a `--dry-run` flag shows the payload
   before it leaves the machine.
5. **Cloud conversion path works on day one** — even if the
   public-profile page is thin. `traitprint push` → a working
   (possibly minimal) `traitprint.com/<handle>` must exist. Otherwise
   the upgrade narrative is aspirational and the audience will notice.
6. **Schema is versioned.** `vault_schema_version` field on disk;
   cloud handles forward-migration on push; `docs/schema-versioning.md`
   documents the policy.
7. **Demo is pre-configured, not live-set-up.** Dry-run twice on the
   actual demo laptop before Tuesday. Pre-recorded screencast as
   fallback.
8. **MCP surface shipped to the registry in the same release window** —
   part of the Tier S distribution bundle already queued.

### Conditional on Monday EOD readiness

If items 5, 7, and 8 cannot all be green by Monday EOD:
- **Announce the initiative at AE Miami** — publish the blog post,
  the spec, the schema, and the repo as a "launching Q2" preview.
- **Do not run the live demo.** Use a screencast of the dev-laptop
  flow and the public GitHub link.
- Time-to-public-ship: aim for 2026-05-31 so the AE Miami blog post
  has a credible delivery date attached.

The *worst* outcome is shipping a broken demo that makes the
local-first pitch feel hollow. The second-worst is quietly pushing
the announcement back without saying so. The first-best outcome is a
clean Tuesday demo; the second-best is "announce now, ship in six
weeks, credibility intact."

### What this unlocks

- **Miami narrative:** *"Here's the open-source local vault. Here's
  the cloud when you want to be findable."* That line alone probably
  converts 10-20 signups from the room.
- **Distribution leverage:** the MCP Registry listing now has a
  SECOND DataViking entry (SynthPanel + Traitprint). Two tools in the
  registry reads as an ecosystem, not a single product.
- **Brand coherence:** SynthBench is open MIT, SynthPanel is open MIT
  with an MCP server, Traitprint-Local is open MIT with an MCP server.
  The "DataViking ships the open layer" story writes itself.
- **Recruiter-side credibility:** enterprises evaluating Traitprint for
  internal use can audit the local client before committing to cloud.
  Security review → yes. This is a real enterprise-sale enabler.
- **Defensive against LinkedIn / incumbents:** the hardest move against
  a walled-garden incumbent is to make yourself *the open standard*.
  Schema-in-the-open is how you do it.

---

## Risks I'd flag but not block on

- **Support surface.** Open-source means GitHub issues. Allocate CPO
  or docs owner to triage; decide what's "supported" vs "community"
  at launch.
- **Telemetry question.** Zero telemetry in the local client is the
  privacy-maximal stance and the one that matches the brand. Opt-in
  diagnostic ping only if it's genuinely anonymous. Do not bundle
  analytics by default.
- **"Local Claude" alternative.** Ollama-based local models exist.
  Make sure `traitprint mcp-serve` works with Ollama-served Claude-
  compatible endpoints, not just cloud Claude. This doubles the
  "entirely local" value prop.
- **Schema lock-in perception.** If users are afraid their vault
  will become useless when they leave, open-source + documented
  schema + `traitprint export` command solve this in one move. Ship
  all three together.

---

## Final word

Green-light. The conditions are non-negotiable; the timeline is
conditional; the narrative unlock is substantial. Build it.

— cpo
