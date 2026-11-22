# vipeAIM 2.0 — Telegram Automation

## Features
- Up to 10 scheduled publishing attempts per day (one story per GitHub Actions run).
- RSS feeds for tech, movies, TV/series, gaming, anime, science and entertainment.
- Gemini-generated factual Bengali headline + Bengali and English summaries. Without Gemini, safe source-title/summary fallback is used.
- Branded 1280×720 graphic thumbnail with category colors and Bengali headline.
- Duplicate protection, publication log, JSON analytics and companion static website.
- Designed for GitHub mobile/browser management.

## Required GitHub Secrets
In repository → Settings → Secrets and variables → Actions → New repository secret:
1. `TELEGRAM_BOT_TOKEN`: BotFather token.
2. `TELEGRAM_CHANNEL_ID`: public channel `@channelusername` or private numeric `-100...` ID.
3. `GEMINI_API_KEY`: optional, for AI-written Bengali headlines and bilingual summaries.

The bot must be an administrator in the channel with permission to post. Never put tokens in source code or share them in screenshots.

## Install from Android
1. Download and unzip this project.
2. In `aim999-crypto/vipeaim`, upload all files/folders to the `main` branch. Keep exact paths, especially `.github/workflows/daily-tech.yml`.
3. If GitHub says a file already exists, open that file and use Edit/replace, or upload the project files one-by-one with exact existing paths. Do not create a second copy such as `daily-tech (1).yml`.
4. Enable Actions: Settings → Actions → General → Allow all actions.
5. Set Workflow permissions to **Read and write permissions** and Save.
6. Open Actions → vipeAIM Daily Publisher → Run workflow.
7. Inspect the run. A successful `Publish one fresh story` step means Telegram accepted the post.

## Schedule
10 scheduled runs in UTC: 02,04,06,08,10,12,14,16,18,20. Bangladesh time (UTC+6): 08:00,10:00,12:00,14:00,16:00,18:00,20:00,22:00,00:00,02:00. Each run publishes one fresh article if available. GitHub may delay scheduled jobs. This is a 10-post target, not a guarantee: RSS sources may not provide 10 unique fresh stories every day.

## Website
Optional companion website is included in `website/`. To deploy:
1. Repository Settings → Pages → Build and deployment → Source: GitHub Actions.
2. Run `Deploy vipeAIM companion website` manually, or wait for a push touching watched files.
3. The Pages URL appears in Settings → Pages.
The publisher mirrors posts and analytics into `website/data/`. Add About, Contact, Privacy Policy, Editorial Policy, original articles and a custom domain before applying for AdSense. Approval is never guaranteed.

## Monetization: important limitations
- Affiliate: add an approved link in `affiliate_links.json`, set `enabled` to `true`, and use a matching category (or `All`). The bot adds a labeled inline button and affiliate disclosure. Use products relevant to the post category. The affiliate network, not this bot, confirms conversions/commission.
- Sponsored: add a real sponsor name/label/URL in `sponsors.json` and set `enabled` to `true`. The bot adds a clearly labeled sponsored section and button to posts. Enable only during a real paid campaign and only after editorial/advertising approval.
- AdSense: AdSense does not monetize Telegram posts. It requires a separate eligible website, original useful content, policy compliance and approval. The included website is a simple companion feed, not enough by itself to guarantee AdSense approval.
- Telegram: native ad revenue/Stars eligibility depends on current Telegram terms, region and account eligibility. Check Telegram channel monetization settings. Code cannot enable or guarantee payouts.
- Tracking: publication log and UTM tags track published links/source campaigns when connected to analytics. Telegram Bot API does not expose individual link clicks. No fake revenue or conversion counts are generated.

## Customize
- `feeds.json`: RSS sources and categories.
- `config.json`: freshness window and Gemini model.
- `.github/workflows/daily-tech.yml`: posting schedule.
- `website/index.html`: companion site design.
- `data/publication_log.csv`: append-only publishing ledger.
- `state.json`: deduplication history.

## Troubleshooting
- No workflow runs: check Actions enabled, workflow file path and default branch.
- Telegram 401: token invalid; rotate it via BotFather and update secret.
- Telegram 403: make bot channel admin and grant post permission; verify channel ID.
- No post sent: no fresh unseen RSS article in configured age window; add trusted feeds or adjust `max_age_hours`.
- Gemini errors: fallback copy is used; check key/quota.
- Bengali thumbnail font: runner downloads Noto Sans Bengali. If that fails, place Noto Sans Bengali TTF files in `assets/`.
- Push rejected: wait for current run to finish, then rerun; workflow rebases before push.

## Editorial and copyright
The thumbnail is a custom graphic, not a copied film poster. News summaries must be factual and linked to the original publisher. Respect RSS terms, image licenses, copyright and corrections. Do not fabricate breaking news, reviews or release dates.
