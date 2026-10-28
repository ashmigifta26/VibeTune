from pathlib import Path
import sqlite3
import json
import os
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from playlist_engine import PlaylistEngine

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "vibetune_users.db"
app = Flask(__name__)
app.secret_key = os.environ.get("VIBETUNE_SECRET_KEY", "local-vibetune-development-key-change-before-deployment")
engine = PlaylistEngine(str(BASE_DIR / "data" / "songs.csv"))


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS user_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            song_id TEXT NOT NULL,
            song_title TEXT NOT NULL,
            artist TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_type, song_id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            songs_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please log in to continue."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not full_name or not email or not password or not confirm_password:
            flash("Please fill in every field.", "error")
        elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            try:
                with get_db() as db:
                    cursor = db.execute(
                        "INSERT INTO users(full_name, email, password_hash) VALUES (?, ?, ?)",
                        (full_name, email, generate_password_hash(password))
                    )
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session["user_name"] = full_name
                    session["user_email"] = email
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("An account with this email already exists. Please log in.", "error")
    return render_template("auth.html", mode="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("auth.html", mode="login")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("index.html", user_name=session.get("user_name", "Music lover"))


@app.route("/api/playlist", methods=["POST"])
@login_required
def playlist():
    payload = request.get_json(silent=True) or {}
    try:
        limit = max(1, min(30, int(payload.get("limit", 8))))
    except (TypeError, ValueError):
        limit = 8
    result = engine.generate(
        request_text=payload.get("request", ""),
        mood=payload.get("mood", "any"),
        genre=payload.get("genre", "any"),
        limit=limit
    )
    return jsonify(result)


@app.route("/api/songs")
@login_required
def songs():
    return jsonify(engine.songs)


@app.route("/api/stats")
@login_required
def stats():
    return jsonify(engine.stats())


@app.route("/api/items", methods=["GET", "POST", "DELETE"])
@login_required
def user_items():
    user_id = session["user_id"]
    if request.method == "GET":
        with get_db() as db:
            rows = db.execute("SELECT item_type, song_id, song_title, artist FROM user_items WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        return jsonify([dict(row) for row in rows])
    payload = request.get_json(silent=True) or {}
    item_type = payload.get("item_type", "queue")
    if item_type not in {"queue", "favorite", "recent"}:
        return jsonify({"error": "Invalid item type."}), 400
    song_id = str(payload.get("song_id", "")).strip()
    song_title = str(payload.get("song_title", "")).strip()
    artist = str(payload.get("artist", "")).strip()
    if not song_id or not song_title:
        return jsonify({"error": "Song details are missing."}), 400
    with get_db() as db:
        if request.method == "POST":
            if item_type == "recent":
                db.execute("DELETE FROM user_items WHERE user_id=? AND item_type='recent' AND song_id=?", (user_id, song_id))
            db.execute("INSERT OR IGNORE INTO user_items(user_id,item_type,song_id,song_title,artist) VALUES(?,?,?,?,?)", (user_id,item_type,song_id,song_title,artist))
            if item_type == "recent":
                db.execute("DELETE FROM user_items WHERE user_id=? AND item_type='recent' AND id NOT IN (SELECT id FROM user_items WHERE user_id=? AND item_type='recent' ORDER BY id DESC LIMIT 25)", (user_id, user_id))
        else:
            db.execute("DELETE FROM user_items WHERE user_id=? AND item_type=? AND song_id=?", (user_id,item_type,song_id))
    return jsonify({"ok": True})


@app.route("/api/playlists", methods=["GET", "POST", "DELETE"])
@login_required
def saved_playlists():
    user_id = session["user_id"]
    if request.method == "GET":
        with get_db() as db:
            rows = db.execute("SELECT id, name, songs_json, created_at FROM playlists WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
        return jsonify([{"id": row["id"], "name": row["name"], "songs": json.loads(row["songs_json"]), "created_at": row["created_at"]} for row in rows])
    payload = request.get_json(silent=True) or {}
    if request.method == "DELETE":
        try:
            playlist_id = int(payload.get("id"))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid playlist."}), 400
        with get_db() as db:
            db.execute("DELETE FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id))
        return jsonify({"ok": True})
    name = str(payload.get("name", "")).strip()[:80]
    songs = payload.get("songs", [])
    if not name or not isinstance(songs, list) or not songs:
        return jsonify({"error": "Enter a playlist name and generate songs first."}), 400
    with get_db() as db:
        cursor = db.execute("INSERT INTO playlists(user_id,name,songs_json) VALUES(?,?,?)", (user_id, name, json.dumps(songs)))
        playlist_id = cursor.lastrowid
    return jsonify({"ok": True, "id": playlist_id, "name": name}), 201


init_db()

if __name__ == "__main__":
    app.run(debug=True)
