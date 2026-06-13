# Career Agent - Product Positioning

**Status:** ✅ Decision Made - Option 2: Agentic Workflow

**Decided:** June 13, 2026
**Rationale:** Emphasizes AI intelligence and multi-step automation while remaining technically accurate

---

## The Confusion

We're currently using multiple terms inconsistently:

| Term | Where Used | Implies |
|------|------------|---------|
| "Plugin" | Installation docs | A component for Claude Code |
| "Workflow" | README, plugin.json | A series of steps |
| "Agent" | GitHub Pages title | An autonomous AI system |
| "Application" | Sometimes | A standalone program |

**This creates confusion about:**
- What users are installing
- How they should use it
- What the boundaries are

---

## What We Actually Built

### Technical Reality

**It's a hybrid system:**

1. **Installation layer:** Claude Code Plugin
   - Distributed via plugin marketplace
   - Installed with `/plugin install career-agent`
   - Provides 5 skills to Claude

2. **Execution layer:** Agentic Workflow
   - Claude AI executes the skills
   - Multi-step automation
   - Human-in-the-loop design
   - Browser automation via Claude in Chrome

3. **Implementation layer:** Python Scripts
   - Standalone scripts can run independently
   - `python src/generate_application.py <role_id>`
   - Requires reportlab dependency
   - No Claude needed for PDF generation

---

## Positioning Options

### Option 1: "Claude Code Plugin" (Primary)
**Tagline:** "A Claude Code plugin for automated job applications"

**Pros:**
- Clear installation method
- Sets expectations about Claude dependency
- Aligns with distribution (marketplace)

**Cons:**
- Undersells the sophistication
- Doesn't emphasize AI/autonomy
- Sounds like a small utility

**Example:**
```markdown
# Career Agent

A Claude Code plugin that automates job applications. Generate tailored
CVs and fill ATS forms with browser automation.

Install: /plugin install career-agent
```

---

### Option 2: "Agentic Workflow" (Current)
**Tagline:** "Agentic job application workflow for Claude Code"

**Pros:**
- Emphasizes AI intelligence
- Highlights multi-step nature
- Technically accurate

**Cons:**
- "Workflow" sounds passive
- Doesn't clarify it's a plugin
- Could mean many things

**Example:**
```markdown
# Career Agent

An agentic workflow for Claude Code that automates job applications.
Multi-step AI automation from job search to ATS form filling.

Install as plugin: /plugin install career-agent
```

---

### Option 3: "AI Agent" (Aspirational)
**Tagline:** "AI agent for automated job applications"

**Pros:**
- Strongest marketing position
- Emphasizes autonomy
- Exciting, modern

**Cons:**
- Technically misleading (it's not fully autonomous)
- Human still in the loop
- Overpromises

**Example:**
```markdown
# Career Agent

An AI agent that handles job applications for you. Searches for roles,
generates tailored CVs, and fills ATS forms automatically.

Powered by Claude Code.
```

---

### Option 4: "Application Suite" (Accurate)
**Tagline:** "Job application automation suite"

**Pros:**
- Acknowledges multiple components
- Doesn't overcommit to single paradigm
- Flexible

**Cons:**
- Generic, boring
- Doesn't highlight AI
- "Suite" sounds enterprise-y

---

## Recommended Positioning

### 🎯 Primary: **Claude Code Plugin**

**Why:**
- That's literally what it is (has plugin.json, marketplace.json)
- That's how users install it
- Sets clear expectations
- Accurate technical framing

**Full Positioning Statement:**

```
Career Agent is a Claude Code plugin that provides an agentic workflow
for automated job applications. It combines AI-powered job search,
tailored CV generation, and browser automation to streamline the entire
application process.
```

**Layered explanation:**
- **What it is:** Claude Code plugin (installation/distribution)
- **What it does:** Agentic workflow (execution model)
- **What it provides:** Automated job applications (value prop)
- **How it works:** AI + browser automation (technical approach)

---

## Consistent Terminology

### Primary Terms (Use These)

| Term | When to Use | Example |
|------|-------------|---------|
| **Plugin** | Installation, architecture, distribution | "Install the plugin with..." |
| **Skills** | Individual commands | "The `/source` skill finds jobs" |
| **Workflow** | Multi-step processes | "The job application workflow" |
| **Automation** | What it provides | "Automate ATS form filling" |
| **Claude** | The AI executing it | "Claude generates your CV" |

### Avoid These

| Term | Why to Avoid | Use Instead |
|------|--------------|-------------|
| "Agent" alone | Implies full autonomy | "Agentic workflow" or "Claude Code plugin" |
| "App" | Implies standalone GUI | "Plugin" |
| "Tool" | Too generic | "Plugin" or "automation" |
| "Platform" | Too enterprise | "Plugin" or "workflow" |

---

## Updated Descriptions

### README.md (First Line)
**Current:**
```markdown
**Agentic job application workflow for Claude Code and Cowork.**
```

**Proposed:**
```markdown
**A Claude Code plugin that automates job applications with AI-powered
workflows.**
```

### plugin.json
**Current:**
```json
"description": "Agentic job application workflow. Generates tailored CV +
cover letter PDFs per role and fills ATS forms via browser automation."
```

**Proposed:**
```json
"description": "Claude Code plugin for automated job applications. Generates
tailored CVs and fills ATS forms with AI-powered browser automation."
```

### GitHub Pages
**Current:**
```html
<title>Career Agent | Autonomous Job Application Agent</title>
```

**Proposed:**
```html
<title>Career Agent | Claude Code Plugin for Job Applications</title>
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  Career Agent                        │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │        Claude Code Plugin                  │    │
│  │  (Installation & Distribution Layer)       │    │
│  └────────────────┬───────────────────────────┘    │
│                   │                                  │
│  ┌────────────────▼───────────────────────────┐    │
│  │        5 Skills (Execution Layer)          │    │
│  │  /source | /new-role | /generate-cv       │    │
│  │  /apply  | /track                          │    │
│  └────────────────┬───────────────────────────┘    │
│                   │                                  │
│  ┌────────────────▼───────────────────────────┐    │
│  │   Python Scripts (Implementation Layer)    │    │
│  │  cv_builder.py | cl_builder.py             │    │
│  │  generate_application.py | tracker.py      │    │
│  └────────────────┬───────────────────────────┘    │
│                   │                                  │
│  ┌────────────────▼───────────────────────────┐    │
│  │     External Dependencies                  │    │
│  │  reportlab | Claude in Chrome              │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## Elevator Pitches

### 10 seconds
"A Claude Code plugin that automates job applications. It generates tailored
CVs and fills ATS forms for you."

### 30 seconds
"Career Agent is a Claude Code plugin that streamlines job applications. It
finds matching roles, generates tailored CVs, fills ATS forms with browser
automation, and tracks your pipeline—all while keeping you in control."

### 60 seconds
"Career Agent is a Claude Code plugin that transforms job hunting. Instead of
manually applying to each role, you install the plugin, set up your profile
once, and then use simple commands like `/source` to find jobs, `/generate-cv`
to create tailored resumes, and `/apply` to fill forms automatically. Claude
handles the tedious work while you stay in control—it never submits without
your final review. It's like having a personal assistant for job applications."

---

## Documentation Hierarchy

### What Users See First

1. **It's a plugin** - Installation instructions
2. **For Claude Code** - Where it runs
3. **That automates job applications** - What it does
4. **Using AI workflows** - How it works
5. **With 5 skills** - What you can do

### What Developers See

1. **Plugin architecture** - Technical structure
2. **Python implementation** - How it's built
3. **Skills system** - How to extend
4. **Browser automation** - Integration points

---

## Competitive Positioning

### vs. Other Job Application Tools

| Them | Us |
|------|-----|
| Standalone apps | Claude Code plugin |
| Static templates | AI-tailored content |
| Manual form filling | Browser automation |
| Generic resumes | Role-specific CVs |
| No AI | Claude-powered |

### vs. Other Claude Plugins

| Them | Us |
|------|-----|
| General utilities | Vertical-specific (job hunting) |
| Single-purpose | End-to-end workflow |
| Text-only | Browser automation |
| No state | Pipeline tracking |

---

## Decision Required

**Choose one primary positioning:**

- [ ] **Option 1:** Claude Code Plugin (Recommended)
- [ ] **Option 2:** Agentic Workflow (Current)
- [ ] **Option 3:** AI Agent (Aspirational)
- [ ] **Option 4:** Application Suite (Safe)
- [ ] **Option 5:** Custom: ___________

**Then update:**
- [ ] README.md
- [ ] plugin.json
- [ ] docs/index.html
- [ ] CLAUDE.md
- [ ] All marketing copy

---

## Open Questions

1. Can it run without Claude Code at all? (Yes - Python scripts standalone)
2. Should we support standalone mode? (TBD)
3. Is "plugin" limiting for future growth? (Maybe)
4. Do we eventually want a desktop app? (Future consideration)

---

**Next Steps:**
1. Choose positioning
2. Update all documentation
3. Ensure consistency across all touchpoints
4. Create brand guidelines document
