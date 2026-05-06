# What Counts As A Program In An Agent OS?

If an agent operating system runs applications, what is an application?

It's not a workflow. It's not a prompt. It's not a single agent. It's a bundle — the AI equivalent of a `.app` directory on macOS. Activating one forks its starter substrate into your workspace. Deactivating leaves your data intact and just removes the program's framing.

I shipped my first program a few months ago — alpha-trader, an autonomous trading operations bundle. I expected it to be an "opinionated configuration." It turned out to be much more than that. It was an actual bundle: portable across workspaces, installable, uninstallable, ship-updatable.

**The three files every program needs**

→ MANIFEST.yaml — machine-readable identity. Slug, status, required platform integrations, declared capabilities, default agent roster, lifecycle phases.
→ README.md — human prose. What the program does, who it's for.
→ SURFACES.yaml — composition manifest. How the cockpit should render when this program is active.

Plus one required directory:

→ reference-workspace/ — the bundle's starter substrate. Tagged by tier (canon, authored, placeholder) so program updates can re-apply infrastructure without overwriting operator-authored content.

**Why activation is a fork, not an install**

When you install Excel on macOS, the binary lives in /Applications/. Your spreadsheets live in ~/Documents/. They're separate.

An agent OS program works the opposite way. Activation forks the bundle's reference workspace into the operator's workspace at the same paths. Why? Because the operator needs to author the substrate the program reasons against — the reviewer's principles, the mandate, the risk envelope. These have to be operator-owned.

Forking on activation means the program ships a great template, the operator customizes, and program updates re-apply boring infrastructure without touching operator voice.

**Why most "agent templates" don't count**

A lot of products ship "templates" you can clone. These aren't programs. They fill in your existing schema. A program declares its own. A template is consumed and forgotten. A program persists, updates, uninstalls.

This is how the agent OS becomes an ecosystem. Templates can't be installed by third parties. Programs can. That's the whole reason the OS pattern won the first time. Almost certainly why it'll win again.

Full essay: yarnnn.com/blog/what-counts-as-a-program-in-an-agent-os

#AIAgents #AgentArchitecture #AgentOS #AIInfrastructure #LLM

---

Kevin is the founder of YARNNN, an agent-native operating system for autonomous knowledge work.
