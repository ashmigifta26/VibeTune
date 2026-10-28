# VibeTune — Smart Playlist Generator

VibeTune is a polished Flask web app for discovering songs, generating mood-based mixes, saving playlists, managing liked tracks and a play queue, and keeping recent selections. The sample catalog contains **150 tracks**. Song metadata is included; VibeTune opens YouTube search results for listening rather than hosting audio files.

## Features
- Signup, login, sign out, session-protected pages, and hashed passwords.
- Responsive dashboard with left navigation, mood cards, genre browsing, and search.
- Mood/genre playlist generation with selectable sizes up to 30 tracks.
- Save, open, and delete named playlists.
- Add/remove liked songs and queue tracks.
- Recent selected-track history.
- Working light/dark theme toggle and compact-card setting (saved in browser).
- Responsive mini-player controls for selecting tracks and opening a YouTube search for the selected song; actual playback happens externally.

## Requirements
Python 3.10+ and pip.

## Run on Windows CMD
Open CMD in the folder containing `app.py` and run:

```cmd
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and create an account. If `.venv` already exists, skip the first command.

## Run on PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Tests
```cmd
python -m unittest tests.py
```

## Project layout
```text
AI_Based_Smart_Playlist_Generator/
├── app.py
├── playlist_engine.py
├── requirements.txt
├── tests.py
├── data/songs.csv
├── templates/auth.html
├── templates/index.html
└── static/app.js, style.css
```

The `vibetune_users.db` database is created automatically. User passwords are stored as hashes. Before deployment, set a strong `VIBETUNE_SECRET_KEY`, disable Flask debug mode, use HTTPS, and review production security.
