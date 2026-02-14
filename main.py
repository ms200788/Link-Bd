import os
import sqlite3
import secrets
import string
import urllib.request
import urllib.parse
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")  # <- ADDED
BASE_URL = os.getenv("BASE_URL")

DB_FILE = "funnel.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS funnels (
            slug TEXT PRIMARY KEY,
            redirect TEXT UNIQUE,
            link TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def generate_slug():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

def generate_redirect():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

def save_funnel(slug, redirect, link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO funnels VALUES (?, ?, ?)", (slug, redirect, link))
    conn.commit()
    conn.close()

def get_by_slug(slug):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM funnels WHERE slug=?", (slug,))
    data = c.fetchone()
    conn.close()
    return data

def get_by_redirect(redirect, slug):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM funnels WHERE redirect=? AND slug=?", (redirect, slug))
    data = c.fetchone()
    conn.close()
    return data

# ================= TELEGRAM =================
def send_message(chat_id, text):
    if not BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode()

    urllib.request.urlopen(urllib.request.Request(url, data=data))

def send_to_channel(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHANNEL_ID,
        "text": text
    }).encode()

    urllib.request.urlopen(urllib.request.Request(url, data=data))

# ================= USER ROUTES =================

@app.get("/{slug}", response_class=HTMLResponse)
async def user_page(slug: str):
    funnel = get_by_slug(slug)
    if not funnel:
        return HTMLResponse("Page Not Found", status_code=404)

    redirect = funnel[1]

    return f"""
    <html>
    <body style="text-align:center;padding-top:100px;font-family:Arial;">
        <h2>Click Continue</h2>
        <a href="/{redirect}/{slug}">
            <button style="padding:15px 30px;font-size:18px;">Continue</button>
        </a>
    </body>
    </html>
    """

@app.get("/{redirect}/{slug}")
async def redirect_page(redirect: str, slug: str):
    funnel = get_by_redirect(redirect, slug)
    if not funnel:
        return HTMLResponse("Invalid Link", status_code=403)

    return RedirectResponse(funnel[2])

# ================= TELEGRAM WEBHOOK =================

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    # OWNER ONLY
    if user_id != OWNER_ID:
        send_message(chat_id, "Not authorized.")
        return {"ok": True}

    if text.startswith("/create"):
        parts = text.split(" ", 1)
        if len(parts) != 2:
            send_message(chat_id, "Usage:\n/create https://example.com")
            return {"ok": True}

        link = parts[1]
        slug = generate_slug()
        redirect = generate_redirect()

        save_funnel(slug, redirect, link)

        # SEND BACKUP TO CHANNEL
        send_to_channel(f"{slug}|{redirect}|{link}")

        send_message(chat_id, f"User URL:\n{BASE_URL}/{slug}")
        send_message(chat_id, f"Redirect URL:\n{BASE_URL}/{redirect}/{slug}")

    return {"ok": True}