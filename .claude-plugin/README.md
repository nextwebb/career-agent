# Career Agent Plugin Marketplace

This directory contains the marketplace configuration for the career-agent plugin.

## Installation

### Via Marketplace (Recommended)

```bash
# Add the marketplace
claude plugin marketplace add nextwebb/career-agent

# Install the plugin
claude plugin install career-agent
```

Or in Claude Code interactive mode:

```
/plugin marketplace add nextwebb/career-agent
/plugin install career-agent
```

### Direct Installation

```bash
# Install directly without marketplace
claude plugin install github:nextwebb/career-agent
```

Or:

```
/plugin install github:nextwebb/career-agent
```

## What's Included

The career-agent plugin provides 6 skills for local job application workflows:

- `/setup-profile [path]` - Build profile.json from a CV, resume, or LinkedIn PDF
- `/source [country] [role_type]` - Find verified open roles matching your profile
- `/new-role [url]` - Scaffold a new role config interactively
- `/generate-cv <role_id>` - Build ATS-optimized CV + cover letter PDFs
- `/apply <role_id>` - Fill safe ATS fields via browser automation and hand off sensitive fields
- `/track [role_id] [status]` - View and update your application pipeline

## Requirements

- Python 3.10+
- `pip install reportlab`
- Claude in Chrome extension (for `/apply` browser automation)

## Documentation

Visit https://nextwebb.github.io/career-agent/ for complete documentation.
