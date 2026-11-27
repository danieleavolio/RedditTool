"""`rpa auth ...`: log in to Reddit, check the credentials, log out."""

from __future__ import annotations

import os
import secrets
import webbrowser

import httpx
import typer
from pydantic import SecretStr

from reddit_analyzer.config import (
    Credentials,
    clear_secrets,
    get_credentials,
    load_settings,
    store_secret,
    update_config_file,
)
from reddit_analyzer.errors import RedditError
from reddit_analyzer.sources.auth import (
    build_authorize_url,
    exchange_code,
    revoke_token,
    wait_for_code,
)
from reddit_analyzer.sources.oauth import RedditClient

app = typer.Typer(help="Manage Reddit credentials.", no_args_is_help=True)


def _fail(exc: Exception) -> typer.Exit:
    typer.echo(f"Error: {exc}", err=True)
    return typer.Exit(1)


@app.command()
def login(
    client_id: str | None = typer.Option(None, "--client-id", help="Reddit app client ID."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Only print the URL."),
) -> None:
    """Authorize this tool in your browser and store the refresh token in the system keyring."""
    settings = load_settings()
    client_id = client_id or settings.reddit.client_id or typer.prompt("Reddit client ID")
    client_secret = os.environ.get("RPA_CLIENT_SECRET") or typer.prompt(
        "Reddit client secret", hide_input=True
    )
    redirect_uri = settings.reddit.redirect_uri
    state = secrets.token_urlsafe(16)
    url = build_authorize_url(client_id, redirect_uri, state)
    typer.echo(f"Authorize the app in your browser:\n{url}")
    if not no_browser:
        webbrowser.open(url)
    typer.echo(f"Waiting for Reddit to redirect to {redirect_uri} ...")

    try:
        with httpx.Client(timeout=settings.collect.timeout_seconds) as http:
            code = wait_for_code(redirect_uri, state)
            tokens = exchange_code(http, client_id, client_secret, code, redirect_uri)
            creds = Credentials(
                client_id=client_id,
                client_secret=SecretStr(client_secret),
                refresh_token=SecretStr(tokens.refresh_token or ""),
            )
            status = RedditClient(creds, settings, http=http).check_auth()
        update_config_file("reddit", {"client_id": client_id, "redirect_uri": redirect_uri})
        store_secret("client_secret", client_secret)
        store_secret("refresh_token", tokens.refresh_token or "")
        store_secret("username", status.username)
    except RedditError as exc:
        raise _fail(exc) from exc
    typer.echo(f"Logged in as u/{status.username}. Credentials saved.")


@app.command()
def test() -> None:
    """Check that the stored credentials work and show the remaining rate limit."""
    try:
        with RedditClient.from_config() as client:
            status = client.check_auth()
    except RedditError as exc:
        raise _fail(exc) from exc
    typer.echo(f"OK: logged in as u/{status.username}")
    if status.ratelimit_remaining is not None:
        typer.echo(
            f"Rate limit: {status.ratelimit_remaining:.0f} requests left, "
            f"{status.ratelimit_used or 0:.0f} used, resets in "
            f"{status.ratelimit_reset_seconds or 0:.0f}s"
        )


@app.command()
def logout() -> None:
    """Revoke the refresh token at Reddit (best effort) and remove stored credentials."""
    try:
        creds = get_credentials()
        if creds.refresh_token:
            with httpx.Client(timeout=15) as http:
                revoke_token(
                    http,
                    creds.client_id,
                    creds.client_secret.get_secret_value(),
                    creds.refresh_token.get_secret_value(),
                )
    except (RedditError, httpx.HTTPError):
        pass  # nothing to revoke, or Reddit unreachable: still remove the local copy
    clear_secrets()
    typer.echo("Logged out. Credentials removed from the system keyring.")
    typer.echo("Environment variables (RPA_*) and config.toml are left untouched.")
