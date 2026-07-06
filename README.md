# Vintage Touring Frame Tracker

Daily sweep of Craigslist and eBay for 56cm 1980s touring frames/bikes:
**Trek 720, Bridgestone T-700, Bridgestone 400, Miyata 1000.** New matches
arrive as Discord notifications (identical on mobile and desktop clients).

## How it works

- **Craigslist** — parses search-results HTML for sfbay + sacramento
  (Craigslist discontinued RSS), then fetches candidate listing pages so size
  and exclusion checks run against the full posting text, not just the title.
  Rate-limited (2s delays, 25 page fetches/run max).
- **eBay** — Browse API (production keyset), bicycle + frame categories,
  national by default because these frames ship cheap and are rare. Set
  `local_pickup_only: true` to restrict to 75 miles of 94559.
- **Filter engine** — model regexes hardened against Trek 7200 hybrids and
  "700c" wheel noise; size window 55–57cm / 22–22.5" (vintage c-c vs c-t
  measurement slop). Listings stating a *wrong* size are dropped; listings
  stating *no* size are notified flagged "size unknown — verify" so a rare
  Miyata 1000 never slips past a lazy seller. Change via `sizing.unknown_size`.
- **Dedup** — `seen.json`, committed back to the repo by the workflow so you
  never get the same listing twice, even across runner restarts.

## Facebook Marketplace — read this

Marketplace has no public API, and scraping it (headless browser + session
cookie) violates Meta's ToS with genuine account-ban risk. Don't automate it.
The native alternative takes two minutes and is actually better (push
notifications within minutes of posting, not daily):

1. In the Marketplace app/site, search each term: `Trek 720`,
   `Bridgestone T700`, `Bridgestone 400 bike`, `Miyata 1000`.
2. Set location to Napa, radius 75 mi (or "shipping available" for frames).
3. Tap the bell / **"Notify me"** toggle on each search.

## Deploy (GitHub Actions, free tier)

1. Create a **private** repo and push this project.
2. Get eBay API keys: https://developer.ebay.com → create app →
   **Production** keyset → note Client ID and Client Secret.
3. Create a Discord webhook: server → channel settings → Integrations →
   Webhooks → New Webhook → copy URL. (Or use an existing private server;
   make yourself a #bike-alerts channel.)
4. Repo → Settings → Secrets and variables → Actions → add:
   - `EBAY_CLIENT_ID`
   - `EBAY_CLIENT_SECRET`
   - `DISCORD_WEBHOOK_URL`
5. Commit an empty state file once: `echo '{}' > seen.json && git add -f seen.json && git commit -m 'init state' && git push`
6. Actions tab → **Daily bike sweep** → *Run workflow* to test. It then runs
   every day at 15:00 UTC (~7–8am Pacific). Edit the cron in
   `.github/workflows/daily.yml` to change cadence — note GitHub schedules can
   drift 15–60 min; irrelevant at daily cadence.

## Run locally instead

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # fill in secrets
python -m agent.main --dry-run       # prints matches, saves nothing
python -m agent.main                 # real run
python test_filters.py               # filter engine test suite
```

Cron it on any always-on machine: `0 7 * * * cd ~/vintage-bike-agent && python -m agent.main`

## Tuning

Everything lives in the config: add models under `targets` (name + regex),
widen `sizing`, add `queries` (broad queries are fine — the filter engine
decides), extend `exclusions`. Craigslist markup changes occasionally; if a
run starts logging "0 listings pulled," check the selectors in
`agent/sources/craigslist.py::_parse_results`.
