---
name: A site's link fetching broke
about: load_media/search_media fails to fetch from a specific site (YouTube, TikTok, Instagram, Threads, etc.)
title: ""
labels: source-broken
---

**Which site/provider?** (e.g. YouTube, TikTok, Instagram Reels, Threads)

**URL that failed** (remove/redact if private)

**What happened?**
Paste the exact error message returned by `load_media`/`search_media`.

**What did you expect?**

**Notes**
Site-specific fetching lives under `src/make_meme/sources/fetchers/` as independent provider
modules, so a fix for one site usually doesn't risk breaking the others -- PRs welcome.
