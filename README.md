# telescope2

**Yet another Discord bot for the DougDoug Discord server.**

[bot.dougdistrict.xyz](https://bot.dougdistrict.xyz)

### Install

With [**Docker:**](https://www.docker.com/products/docker-desktop)

```sh
git clone --recurse-submodules -j8 git@github.com:tonyzbf/telescope2.git
cd telescope2
docker compose build
```

### Setup

```sh
docker compose run bot ./bin/init
```

You will be prompted for you Discord app ID, secret, and bot token.

This will also setup additional Django settings and a Django superuser for site administration.
You will need to fill in:

For settings:

- `ALLOWED_HOSTS`: space-separated lists of hosts to whitelist; should be your website.

For creating the superuser:

- Your Discord user name `username#discriminator`;
- Your Discord ID (must be correct or the control panel will flag you as a regular user when you login with your Discord account);
- A _new_ password for the superuser. **This is not your Discord password.**

### Run

```sh
docker compose up
```

The bot will be online and the web interface will be at `localhost:8088`.

### Updates

Pull updates, then

```sh
docker compose build
docker compose run bot ./bin/migrate
```