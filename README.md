# Daily Tech BD — Telegram Automation

A phone-friendly GitHub Actions project that publishes up to five fresh tech stories per day to a Telegram channel. Posts are bilingual (Bangla + English), HTML-formatted, and include a source link.

## 1) Create a Telegram bot

1. Open Telegram and message **@BotFather**.
2. Send `/newbot`, follow the prompts, and copy the bot token.
3. Add the bot to your Telegram channel as an **administrator** with permission to post messages.
4. For a public channel, `TELEGRAM_CHANNEL_ID` can be `@YourChannelUsername`. For a private channel, use its numeric chat ID (often starts with `-100`).

Never share your bot token or API keys in chat, code, screenshots, or a public repository.

## 2) Upload this project to GitHub from Android

1. Download and extract this ZIP on your phone.
2. In GitHub, create a new repository, e.g. `daily-tech-telegram`.
3. Upload all files and folders from the extracted project. Keep `.github/workflows/daily-tech.yml` in exactly that path.
4. Ensure the repository is not exposing any secrets. The bot token and keys belong only in GitHub Secrets.

## 3) Add GitHub Secrets

Open repository → **Settings → Secrets and variables → Actions → New repository secret**.

Create these secrets:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | `@YourChannelUsername` or private channel ID |
| `GEMINI_API_KEY` | Optional Google AI Studio API key |

Without `GEMINI_API_KEY`, the project still posts source-based fallback text, but the summaries will not be AI-written. Gemini API usage may have quotas or charges depending on Google's current terms and your account.

## 4) Enable Actions

1. Open the repository's **Actions** tab.
2. If prompted, enable GitHub Actions.
3. Open **Daily Tech Telegram Publisher**.
4. Tap **Run workflow** to test a post immediately.
5. Check your Telegram channel and the Actions run log.

The schedule is set to Bangladesh time (UTC+6): 08:00, 11:00, 14:00, 17:00 and 20:00.

## How the automation works

- Reads the RSS feeds listed in `feeds.json`.
- Selects one recent article not already published.
- Uses Gemini, when configured, to create a concise bilingual summary.
- Sends an HTML-formatted message through the official Telegram Bot API.
- Saves published article IDs in `state.json` to reduce duplicates.

## Important limitations

- The schedule attempts five publishing runs per day; it cannot guarantee five posts if feeds have fewer than five new eligible stories, if a feed is down, or if GitHub Actions is delayed.
- GitHub scheduled workflows can be delayed and may be disabled after long periods of repository inactivity. Use **Run workflow** for manual testing.
- This project sends text posts with source links. It does not copy or rehost publisher photos.
- Review AI-generated summaries and sources periodically. AI can make mistakes; source links are included so readers can verify.
- Respect publisher terms, RSS feed terms, copyright, and attribution requirements.
- GitHub Actions free usage limits and Google's Gemini API terms/quotas may change.

## Customize feeds

Edit `feeds.json` and add/remove RSS feeds in this format:

```json
[
  {"name": "Example Tech", "url": "https://example.com/feed.xml"}
]
```

## Change post times

Edit the five cron expressions in `.github/workflows/daily-tech.yml`. GitHub cron uses UTC. Bangladesh is UTC+6.

## Troubleshooting

- **Telegram 401:** check `TELEGRAM_BOT_TOKEN`.
- **Telegram 403 / chat not found:** add the bot as channel admin and check `TELEGRAM_CHANNEL_ID`.
- **No post:** check the Actions log; there may be no new articles within the 72-hour window.
- **No Bangla AI summary:** verify `GEMINI_API_KEY`; without it the script uses a fallback template.
