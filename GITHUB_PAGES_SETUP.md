# GitHub Pages Setup Guide

## Enable GitHub Pages

1. Go to your repository settings: `https://github.com/nextwebb/career-agent/settings/pages`

2. Under **Source**, select:
   - Branch: `main`
   - Folder: `/docs`

3. Click **Save**

4. Wait 1-2 minutes for deployment

5. Visit: **https://nextwebb.github.io/career-agent/**

## Custom Domain (Optional)

To use a custom domain:

1. In repository settings > Pages > Custom domain, enter your domain (e.g., `career-agent.dev`)
2. Add a `CNAME` file to `/docs/` containing your domain
3. Configure DNS at your domain registrar:
   - For apex domain: Create `A` records pointing to GitHub's IPs
   - For subdomain: Create `CNAME` record pointing to `nextwebb.github.io`

## Local Testing

To test the site locally:

```bash
cd docs
python3 -m http.server 8000
```

Then visit: `http://localhost:8000`

## Features

The landing page includes:

- ✅ Dark/Light theme toggle with localStorage persistence
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Interactive skills tabs (/source, /new-role, /generate-cv, /apply, /track)
- ✅ Sticky sidebar navigation
- ✅ FAQ accordion
- ✅ Terminal-style code examples
- ✅ ATS platform cards with status indicators
- ✅ "How it works" pipeline visualization

## Updating Content

All content is in `docs/index.html`. The page uses:

- **Tailwind CSS** (loaded via CDN)
- **Google Fonts**: Geist, Inter, JetBrains Mono
- **Material Symbols** for icons
- No build step required - pure HTML/CSS/JS
