import os
import time
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# ================= CONFIG =================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DB SETUP =================
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    future=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True)
    target = Column(String)

Base.metadata.create_all(bind=engine)

# ================= APP =================
app = FastAPI()

# ================= CACHE =================
LINK_CACHE = {}
REQUEST_LOG = {}

# ================= HELPERS =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_admin(password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Forbidden")

# ================= HEALTH =================
@app.get("/health")
async def health():
    return {"status": "alive"}

# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2>Fast Link Gateway</h2>"

# ================= ADMIN =================
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:system-ui;background:#141e30;color:#fff}
.card{background:#fff;color:#000;border-radius:16px;padding:18px;margin:20px auto;max-width:420px}
input,button{width:100%;padding:12px;margin:8px 0;border-radius:10px}
button{background:#ff416c;color:#fff;border:none;font-size:16px}
</style>
</head>
<body>
<div class="card">
<h2>Admin Panel</h2>
<form method="post">
<input name="password" placeholder="Admin password">
<input name="slug" placeholder="Short code (movie1)">
<input name="target" placeholder="Target URL">
<button>Create Link</button>
</form>
</div>
</body>
</html>
"""

@app.post("/admin")
async def admin_create(
    password: str = Form(...),
    slug: str = Form(...),
    target: str = Form(...),
    db=Depends(get_db)
):
    check_admin(password)

    link = Link(slug=slug, target=target)
    db.add(link)
    db.commit()

    LINK_CACHE[slug] = target

    return {
        "created": True,
        "short_url": f"https://fast-link-2cmx.onrender.com/go/{slug}"
    }

# ================= AD PAGE =================
@app.get("/go/{slug}", response_class=HTMLResponse)
async def ad_page(slug: str, request: Request, db=Depends(get_db)):
    ip = request.client.host
    now = time.time()
    if now - REQUEST_LOG.get(ip, 0) < 1:
        raise HTTPException(status_code=429)
    REQUEST_LOG[ip] = now

    target = LINK_CACHE.get(slug)
    if not target:
        link = db.query(Link).filter(Link.slug == slug).first()
        if not link:
            return "Invalid link"
        target = link.target
        LINK_CACHE[slug] = target

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0f2027;color:#fff;font-family:system-ui}}
.card{{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}}
.btn{{background:#ff4b2b;color:#fff;border:none;padding:14px;width:100%;border-radius:30px}}
</style>
<script>
let t=10;
setInterval(()=>{{
document.getElementById("t").innerText=t;
if(t--<=0)document.getElementById("c").style.display="block";
}},1000);
</script>
</head>
<body>
<div class="card">
<h3>Sponsored</h3>
<p>Wait <b id="t">10</b> seconds</p>
</div>
<div class="card" id="c" style="display:none">
<a href="/redirect/{slug}">
<button class="btn">Continue</button>
</a>
</div>
</body>
</html>
"""

# ================= REDIRECT =================
@app.get("/redirect/{slug}")
async def final_redirect(slug: str, db=Depends(get_db)):
    target = LINK_CACHE.get(slug)
    if not target:
        link = db.query(Link).filter(Link.slug == slug).first()
        if not link:
            return RedirectResponse("/")
        target = link.target
        LINK_CACHE[slug] = target
    return RedirectResponse(target)