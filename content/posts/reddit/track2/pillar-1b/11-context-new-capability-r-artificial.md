---
title: "The AI industry spent 3 years racing on model capability. I think the next race is about something different: context."
track: 2
target: r/artificial
pillar: 1b
status: ready
---

For the past three years, the AI capability race has been the main event. Larger models. Better reasoning. Higher benchmark scores. Every release cycle brings a new frontier model that's smarter than the last.

The results are extraordinary. Claude, GPT-4, Gemini, Llama — these models can reason through complex problems, write production code, and analyze nuanced situations at a level that would've seemed impossible five years ago.

But something interesting is happening: the models are converging. The gap between first and second place is shrinking. Claude matches GPT-4 in many tasks. Gemini closed the gap in others. Open-source reached production quality for a growing range of use cases. Every few months the frontier moves — and every product built on the previous frontier is left with a temporary advantage that's about to be matched.

**If capability is converging, what differentiates AI products?**

I think the answer is context — specifically, how deeply the system understands the individual user's work.

Here's the practical reality: ask any AI model to produce real work output — a client status update, a project brief, an investor report — and the bottleneck isn't that the model isn't smart enough. It's that the model doesn't know anything about your actual work. Your clients, your projects, what happened this week, the patterns in your communication. The model has the *skill* to produce the work. It lacks the *knowledge* to make it useful.

**Capability = what the model can do.**
**Context = what the model knows about your work.**

For real work output, context wins. An AI using a solid (not frontier) model but with three months of accumulated understanding of your Slack, email, Notion, and calendar will produce dramatically better work output than a frontier model that knows nothing about you.

The implications are significant:

1. **Model switching costs are near zero.** If a better model ships, products can swap it in. Context switching costs are high — three months of accumulated understanding doesn't transfer.

2. **"AI-powered" becomes meaningless.** When every product has access to the same frontier models, the label is table stakes. The question shifts from "is it AI-powered?" to "what does it know about my work?"

3. **The moat moves up the stack.** The moat isn't the model (commoditizing). It's the platform layer — integrations, accumulated context, persistent memory, workflow orchestration. The things that are user-specific and compound over time.

4. **Building gets harder.** Capability improvements are centralized — Anthropic, OpenAI, Google invest billions and every product benefits. Context has to be built per-user, from their specific platforms, accumulated over time. There's no general-purpose shortcut.

I've been building around this thesis with yarnnn — a product where the primary investment isn't model optimization but context infrastructure. Continuous sync from work platforms, accumulated understanding that deepens over time, cross-platform synthesis that connects signals across Slack, email, docs, and calendar. The model is a component (Claude); the context layer is the product.

The capability race isn't over — models will keep improving. But capability is becoming table stakes. The next wave of differentiation seems like it'll come from who can build the deepest understanding of each user's work world.

What do you all think? Is "context is the new capability" too strong a claim, or does it match what you're seeing in the space?
