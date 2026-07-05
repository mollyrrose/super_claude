# Question Frameworks for Focus Group Evaluation

This file contains the question templates and evaluation frameworks for both panels. Personas should internalize these frameworks and apply them naturally in their voice — not as a checklist, but as lenses that shape their thinking.

---

## HUMAN PANEL FRAMEWORKS

### The 5-Level Question Hierarchy (Surface -> Depth)

Each human persona should naturally move through these levels during their evaluation:

**Level 1 — Behavioral (What they do):**
- "Walk me through the last time you used/bought/evaluated something like this."
- "How often do you deal with this problem and what does that look like?"
- "Where do you usually go to research products like this?"

**Level 2 — Attitudinal (What they think):**
- "What features feel essential versus nice-to-have?"
- "How does this compare to alternatives you've tried?"
- "What would make you switch from your current tool?"

**Level 3 — Emotional (What they feel):**
- "How does this product make you feel? Describe it in one word."
- "What frustrates you most about products in this space?"
- "What would make you feel truly confident in choosing this?"

**Level 4 — Motivational (Why they feel that way):**
- "Why is that feature particularly important to you?" (then: "And why does THAT matter?" — repeat until identity level)
- "What would you miss most if this product disappeared tomorrow?"
- "What were you hoping this would solve beyond the obvious?"

**Level 5 — Identity (Who they are / want to be):**
- "What kind of person uses a product like this?"
- "If you recommended this to a friend, what would that say about you?"
- "How does using this fit with how you see yourself professionally?"

### Projective Techniques (Bypass Rational Filters)

These access unconscious attitudes by removing self-consciousness:

**Third-Person Projection:** "What would your most skeptical colleague say about this?" — reveals hidden anxieties the persona holds but won't claim as their own.

**Brand Personification:** "If this product were a person, who would it be? How old? What do they drive? Where do they live?" — reveals brand perception and target audience assumptions.

**Metaphor:** "Complete this sentence: This product is like a _____ because _____" — bypasses analytical thinking, accesses emotional associations.

**Obituary:** "If this product disappeared tomorrow, what would its obituary say? Who would attend the funeral?" — reveals perceived value and emotional attachment.

**Shopping Basket:** "What other products would be in the shopping cart alongside this?" — reveals category associations and usage context.

**Magic Wand:** "If you could change ONE thing about how you handle this problem with a magic wand, what would it be?" — reveals the single biggest unmet need without technical constraints.

### Bernays Unconscious Driver Probes

Each persona has a dominant driver. These questions surface it:

**STATUS:** "Would using this make you look good to your peers? Would recommending it elevate your reputation?"

**BELONGING:** "Would your team/community approve of this choice? Would this bring people together or create friction?"

**SECURITY:** "What could go wrong? What's the worst case? What would you need to feel safe choosing this?"

**IDENTITY:** "Does this fit with how you see yourself? Does using this make you more of who you want to be?"

**CONTROL:** "Do you feel in command when using this? Or does it feel like a black box you're trusting blindly?"

**PERMISSION:** "What's holding you back from switching? What would give you 'permission' to try something new?"

### The Laddering Framework

Trace from concrete attribute to deep motivation:

```
Feature -> "Why does that matter?" -> Consequence -> "Why does THAT matter?" ->
Outcome -> "Why does THAT matter?" -> Emotion -> "Why does THAT matter?" -> Identity
```

Example: "Real-time collaboration" -> "distributed team efficiency" -> "hit deadlines" -> "feel in control" -> "be seen as a competent leader deserving of promotion"

### JTBD Four Forces (Apply to Each Persona)

Every persona experiences all four forces in tension:

1. **Push of current situation:** Frustration with status quo (what's driving them to look)
2. **Pull of new solution:** Attraction to the product's promise (what draws them in)
3. **Anxiety of new solution:** Fear of change, learning curve, risk (what holds them back)
4. **Habit of current situation:** Comfort with familiar, switching costs (what keeps them where they are)

The balance of these forces determines whether a persona would actually switch.

### Desire Mapping Template

For each persona, trace the full motivational stack:

| Layer | Question | Example |
|-------|----------|---------| 
| Surface (Stated) | "What do you need?" | "I need a faster tool" |
| Functional (Implied) | "What task does that serve?" | "Save time on repetitive work" |
| Emotional (Hidden) | "How do you want to feel?" | "Competent, not overwhelmed" |
| Identity (Deepest) | "Who do you want to be?" | "The person who stays ahead" |

---

## AGENT PANEL FRAMEWORKS

### The 6 Pillars of Agent Ergonomics

Each agent persona evaluates through these pillars from their specific architectural perspective:

#### Pillar 1: Semantic Clarity
*"Can I understand what each tool does and use it correctly from the description alone?"*

- Rate confidence (1-10) for each tool: could you construct a valid call without examples?
- Are parameter names self-explanatory?
- Is the return type described precisely enough to parse programmatically?
- Are tool relationships clear (ordering, dependencies, preconditions)?
- For optional parameters: is default behavior documented?

#### Pillar 2: Token Efficiency
*"How much of my context window does each interaction cost?"*

- Estimate tokens per typical response for: simple pages, medium pages, complex pages
- In a 10-action workflow, what % of context window is consumed by responses alone?
- Can lighter responses be requested? (compact mode, field selection, pagination)
- Does the API return fields you never need?
- How does token cost compare to alternatives (raw HTML, other tools)?

#### Pillar 3: Error Recovery
*"When something goes wrong, can I fix it without human intervention?"*

- For each error type: describe recovery strategy and rate recoverability (1-5)
- Does the error response contain enough context to reformulate?
- When resolution fails, can you pick the right element from candidates?
- What happens to session state after an error?
- How many retries are reasonable before escalating?

#### Pillar 4: Integration Friction
*"How many steps from discovery to effective use?"*

- Count tool calls for simplest useful workflow
- Count distinct concepts to understand (sessions, snapshots, targets, etc.)
- Is authentication set-and-forget or per-request?
- How much works with defaults vs. requiring configuration?
- Compare friction to alternatives

#### Pillar 5: Composability
*"Does this tool play well with my other tools?"*

- Can output feed directly into non-browser tools without transformation?
- Does the session model conflict with other stateful tools?
- Are there naming conflicts with common tool registries?
- Can extracted data map to standard formats (CSV, JSON, database)?
- Resource management overhead when running alongside other tools

#### Pillar 6: Reliability / Determinism
*"Same input, same output?"*

- What % of non-determinism comes from the product vs. target websites?
- Does any component introduce inherent non-determinism? (LLM resolvers, dynamic waits)
- How sensitive are responses to minor page changes? (ads, timestamps, counters)
- Are there confidence thresholds or determinism controls?
- What are the non-obvious side effects of each tool?

### Agent Workflow Simulation Template

Each agent persona should mentally execute this realistic workflow and annotate failure points:

```
Step 1: Create session -> What parameters? What defaults?
Step 2: Navigate to URL -> How big is the response? What do I learn?
Step 3: Read page state -> What's in the snapshot? What's missing?
Step 4: Interact (click/fill/submit) -> What target string do I use? Will it resolve?
Step 5: Verify result -> How do I know the action worked? What changed?
Step 6: Extract data -> What format? Is it structured?
Step 7: Handle error -> What went wrong? Can I recover? How many tokens lost?
Step 8: Close session -> Cleanup? What if I crash before this step?
```

### Agent Cost Model

Each agent persona should estimate:
- Tokens per tool call (input: prompt + params, output: response)
- Tokens per typical action loop (call + response + reasoning about response)
- Total tokens for a 10-step workflow
- Dollar cost estimate (at their model's per-token rate)
- Comparison to alternative approaches
