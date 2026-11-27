# Reddit credentials

Reddit Post Analyzer talks to the official Reddit API with OAuth. It ships **no keys**: you
use your own app, approved by Reddit. There is no anonymous fallback (it is against Reddit's
Responsible Builder Policy).

> **Status of Reddit's Data API (checked 27 Nov 2026).** Reddit stopped accepting new
> Data API access requests on 31 Oct 2026 and plans to end remaining public access in March
> 2027. If you already have an approved app, the tool works for as long as Reddit keeps it
> active. If you do not, see [No key?](#no-key) below.

## If you already have an approved app

The app must be of type **web app** or **installed app**. The `password` grant (script apps)
is not supported: it does not work with 2FA.

1. Open <https://www.reddit.com/prefs/apps> with the account that owns the app.
2. Note the **client ID** (the string under the app name) and the **client secret**. Never
   paste the secret in screenshots or chat; if it leaked, regenerate it.
3. Set the app's **redirect URI** to exactly `http://localhost:8080`.
4. If Reddit emailed you about registration or migration, **reply**: apps that do not respond
   lose access from 12 Jan 2027.
5. Log in:

   ```
   rpa auth login      # asks for client ID and secret, opens your browser to authorize
   rpa auth test       # calls /api/v1/me and shows the remaining rate limit
   rpa auth logout     # revokes the token and removes it from your keyring
   ```

The refresh token and client secret are stored in your system keyring, never in plain text.
The client ID and redirect URI go to `config.toml`. The Reddit username is read from
`/api/v1/me`.

### Environment variables (CI, headless machines)

| Variable | Meaning |
|---|---|
| `RPA_CLIENT_ID` | client ID |
| `RPA_CLIENT_SECRET` | client secret |
| `RPA_REFRESH_TOKEN` | refresh token (needed when there is no keyring) |
| `RPA_REDIRECT_URI` | default `http://localhost:8080` |

Environment variables win over `config.toml` and the keyring.

## No key?

- **Researchers** (university or research institution): apply to
  [Reddit for Researchers](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program).
- **Developers**: check the
  [Reddit Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki)
  and the changelogs in case the request channel reopens. Send one request per use case:
  duplicates violate the policy.
- **Commercial use** needs a written agreement with Reddit.

Using Reddit data to train ML/AI models, or commercially, requires Reddit's written approval.
