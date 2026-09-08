# Authentication setup

This is a self-hosted, open-source bot: **every operator provides their own
credentials.** Nothing is bundled or shared between installs. You'll need
three separate things.

## 1. Discord bot token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   and create a new application.
2. In **Bot**, click **Reset Token** / **Copy** to get your bot token. Put it
   in `.env` as `DISCORD_TOKEN`.
3. Enable **Message Content Intent** only if you plan to add prefix
   commands later — the bundled slash commands don't need it.
4. Under **OAuth2 → URL Generator**, select scopes `bot` and
   `applications.commands`, and permissions `Connect`, `Speak`,
   `Send Messages`, `Embed Links`. Use the generated URL to invite the bot
   to your server.

## 2. Spotify Web API app (catalog search)

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   and create an app (any name/description; no redirect URI is required
   since we only use the Client Credentials flow).
2. Copy the **Client ID** and **Client Secret** into `.env` as
   `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`.
3. This flow is app-only — no Spotify account of yours ever logs in through
   it, and it doesn't require Premium. It's only used to resolve
   `/play <song name>` into a Spotify track URI.

## 3. Spotify Soloist (the account that actually plays audio)

This step requires a **Spotify Premium** account — the one whose music will
actually be heard in the voice channel.

1. In the same [Spotify Developer Dashboard](https://developer.spotify.com/dashboard),
   find the **Spotify Soloist API key** section and generate a key. Keep it
   secret — treat it like a password (never commit it, never share it).
2. Install `soloist` on the machine that will play audio (see
   `spotify/soloist` for install instructions for your Linux
   distribution/Raspberry Pi).
3. Run `scripts/setup_pulse_sink.sh` on that machine to create the
   PulseAudio null-sink Soloist will play into (instead of real speakers).
4. Launch Soloist pointed at that sink and with the WebSocket API enabled
   — see `scripts/run_soloist.sh.example` for the exact command.
5. **Pairing**: open the Spotify app on any device on the same network,
   open the Connect device picker, and select your Soloist device
   (e.g. "Discord Bot"). Soloist stores the session after this — you won't
   need to re-pair on every restart. There's no browser login or password
   prompt in this flow.
6. Set `SOLOIST_WS_HOST` / `SOLOIST_WS_PORT` in `.env` to match what you
   passed to `--ws` (use `127.0.0.1` unless you're doing the SSH-tunnel
   deployment — see [DEPLOYMENT.md](DEPLOYMENT.md)).

Once all three are set in `.env`, run the bot with `python -m bot.main`.
