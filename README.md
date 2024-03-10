# Telegram Download Daemon Radarr

A Telegram Daemon (not a bot) for file downloading automation for channels of which you have admin privileges Into Radarr.

If you have got an Linux Server With Radarr and you want to automate file downloading from Telegram channels into Radarr, this daemon is for you.

Telegram bots are limited to 20Mb file size downloads. So this agent or daemon allow bigger downloads (limited to 2GB by Telegram APIs).

It Can look Bugy but it works Perfect


# Changes i Made
- Added Download Progress Bar.
- Added Moving satus on file move to destination.
- Added Rename To the File.
- Some Functions, Messages Tweaks

# Docker Setup:

| Environment Variable     | Command Line argument | Description                                                  | Default Value       |
|--------------------------|:-----------------------:|--------------------------------------------------------------|---------------------|
| `TELEGRAM_DAEMON_API_ID`   | `--api-id`              | api_id from https://core.telegram.org/api/obtaining_api_id   |                     |
| `TELEGRAM_DAEMON_API_HASH` | `--api-hash`            | api_hash from https://core.telegram.org/api/obtaining_api_id |                     |
| `TELEGRAM_DAEMON_DEST`     | `--dest`                | Destination path for downloaded files                       | `/telegram-downloads` |
| `TELEGRAM_DAEMON_TEMP`     | `--temp`                | Destination path for temporary (download in progress) files                       | use --dest |
| `TELEGRAM_DAEMON_CHANNEL`  | `--channel`             | Channel id to download from it (Please, check [Issue 45](https://github.com/alfem/telegram-download-daemon/issues/45), [Issue 48](https://github.com/alfem/telegram-download-daemon/issues/48) and [Issue 73](https://github.com/alfem/telegram-download-daemon/issues/73))                              |                     |
| `TELEGRAM_DAEMON_DUPLICATES`  | `--duplicates`             | What to do with duplicated files: ignore, overwrite or rename them | rename                     |
| `TELEGRAM_DAEMON_WORKERS`  | `--workers`             | Number of simultaneous downloads | Equals to processor cores                     |

You can define them as Environment Variables, or put them as a command line arguments, for example:

    python telegram-download-daemon.py --api-id <your-id> --api-hash <your-hash> --channel <channel-number>


# docker-compose
```bash
version: "3"
services:
  telegram-download-daemon-radarr:
    #build:
    image: randomg1/telegram-download-daemon-radarr:6
    container_name: telegram-download-daemon-radarr
    read_only: true
    environment:
      TELEGRAM_DAEMON_API_ID: "api_id"
      TELEGRAM_DAEMON_API_HASH: "api_hash"
      TELEGRAM_DAEMON_CHANNEL: "channel_id"
      TELEGRAM_DAEMON_TEMP: "/downloads"
      TELEGRAM_DAEMON_DEST: "/movies"
      TELEGRAM_DAEMON_SESSION_PATH: "/session"
      TELEGRAM_DAEMON_DUPLICATES: "ignore"
      TELEGRAM_DAEMON_WORKERS: 7
    volumes:
      - ${MEDIA_DIRECTORY}/downloads:/downloads
      - ${MEDIA_DIRECTORY}/movies:/movies
      - ${MEDIA_DIRECTORY}/sessions:/session
    restart: unless-stopped
```

# How to login
- after docker-compose setup
- You need to **interactively** run the container for the first time.
- When you use `docker-compose`, the `.session` file, where the login is stored is kept in *Volume* outside the container. Therefore, when using docker-compose you are required to:

```bash
$ docker-compose run --rm telegram-download-daemon-radarr
# Interact with the console to authenticate yourself.
# See the message "Signed in successfully"
# Close the container
$ docker-compose up -d
```

# How to use with Radarr:
- Radarr Movie Folder Format Should be "{Movie Title} ({Release Year})"
- Temp Could be radarr "/downloads" or whatever you want.
- Destination need to be radarr "/movies"
- After Telegram Login, restart the server.
- You should be prompted with a message that the bot is on, on the channel you chose
- Mnaully add the specified movie on Radarr, the daemon cant do it.
- Forward A File To The Channel, while forwarding you have to add the movie name year in this format "{Movie Title} ({Release Year})", or else it doesnt procced to the download part.

# Bot Functions:
* Say "/status" to the daemon to check the current status of downloads.
* Say "/clean" to remove stale (*.tdd) files from temporary directory.
* Say "/queue" to list the pending files waiting to start.
