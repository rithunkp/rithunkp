# Phase 2 - Self-hosted GitHub stats

Do not use the public `github-readme-stats` instance for the main stats cards. It is shared by many profiles and often returns `API rate limit exceeded`. Self-hosting gives your README its own Vercel deployment and lets it use your own GitHub token privately.

## 1. Create a GitHub classic token

1. Open GitHub.
2. Go to **Settings** from your profile menu.
3. Open **Developer settings**.
4. Open **Personal access tokens**.
5. Choose **Tokens (classic)**.
6. Click **Generate new token**, then **Generate new token (classic)**.
7. Give it a clear note, for example `github-readme-stats-vercel`.
8. Set **Expiration** to **No expiration**.
9. Select the **repo** scope.
10. Generate the token.
11. Copy it immediately.

Never paste this token into your README, a GitHub issue, chat, or any public place. You will only put it into Vercel as a private environment variable.

## 2. Fork github-readme-stats

1. Open `https://github.com/anuraghazra/github-readme-stats`.
2. Click **Fork**.
3. Keep the fork under your GitHub account.

## 3. Deploy the fork on Vercel

1. Open `https://vercel.com`.
2. Sign up or sign in with GitHub.
3. Use the **Hobby** plan.
4. Click **Add New...**.
5. Choose **Project**.
6. Import your fork of `github-readme-stats`.
7. In the project setup, add an environment variable:

```text
PAT_1 = your GitHub classic token
```

8. Deploy the project.
9. Copy the production deployment URL, for example:

```text
https://your-github-readme-stats.vercel.app
```

## 4. Send me the Vercel URL

After deployment, send me the Vercel URL. I will replace `YOUR_STATS_INSTANCE` in `README.md` with your real instance and verify the themed card URLs.

## Why `hide_rank=true`

The default stats rank is weighted heavily by stars. For newer accounts or builders with useful private/local work, it can be misleading. The card is better here as a compact activity summary, so the README uses `hide_rank=true`.
