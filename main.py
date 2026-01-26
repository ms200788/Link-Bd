import os
import time
import random
import string
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# ================= CONFIG =================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./links.db")  # default sqlite

BASE_URL = "https://fast-link-2cmx.onrender.com"

# ================= DB SETUP =================
engine = create_engine(
    DATABASE_URL,
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
    clicks = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    created_at = Column(Integer)

Base.metadata.create_all(bind=engine)

# ================= APP =================
app = FastAPI()

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

def generate_slug(length=6):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

# ================= HEALTH =================
@app.get("/health")
async def health():
    return {"status": "alive"}

# ================= ADMIN LOGIN =================
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f2027;color:#fff;font-family:system-ui}
.card{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}
input,button{width:100%;padding:14px;margin-top:10px;border-radius:12px}
button{background:#ff4b2b;color:#fff;border:none}
</style>
</head>
<body>
<div class="card">
<h3>Admin Login</h3>
<form method="post" action="/admin/login">
<input type="password" name="password" placeholder="Admin Password" required>
<button>Login</button>
</form>
</div>
</body>
</html>
"""

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        return HTMLResponse("<h2 style='text-align:center;color:red'>Invalid Password</h2><a href='/admin/login'>Back</a>")
    # redirect to admin panel
    return RedirectResponse("/admin/panel")

# ================= ADMIN PANEL =================
@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(db=Depends(get_db)):
    links = db.query(Link).all()
    rows = ""
    for l in links:
        rows += f"<tr><td>{l.slug}</td><td>{l.target}</td><td>{l.clicks}</td><td>{l.completed}</td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(l.created_at))}</td></tr>"
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0f2027;color:#fff;font-family:system-ui}}
.card{{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}}
input,button{{width:100%;padding:12px;margin-top:8px;border-radius:12px}}
button{{background:#4caf50;color:#fff;border:none}}
table{{width:100%;border-collapse:collapse;margin-top:16px}}
th,td{{border:1px solid #000;padding:8px;text-align:center}}
</style>
</head>
<body>

<div class="card">
<h3>Create Funnel Link</h3>
<form method="post" action="/admin/create">
<input type="url" name="target" placeholder="Target URL" required>
<button>Create Link</button>
</form>
</div>

<div class="card">
<h3>All Links</h3>
<table>
<tr><th>Slug</th><th>Target</th><th>Clicks</th><th>Completed</th><th>Created At</th></tr>
{rows}
</table>
</div>

</body>
</html>
"""

@app.post("/admin/create", response_class=HTMLResponse)
async def admin_create_link(target: str = Form(...), db=Depends(get_db)):
    slug = generate_slug()
    while db.query(Link).filter(Link.slug == slug).first():
        slug = generate_slug()
    link = Link(slug=slug, target=target, clicks=0, completed=0, created_at=int(time.time()))
    db.add(link)
    db.commit()
    full_url = f"{BASE_URL}/go/{slug}"
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0f2027;color:#fff;font-family:system-ui}}
.card{{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}}
input{{width:100%;padding:12px}}
button{{background:#4caf50;color:#fff;border:none;padding:14px;width:100%;border-radius:30px}}
</style>
<script>
function copyLink(){{
  let i=document.getElementById("l");
  i.select();
  document.execCommand("copy");
  alert("Copied");
}}
</script>
</head>
<body>

<div class="card">
<h3>Link Created</h3>
<input id="l" value="{full_url}" readonly>
<button onclick="copyLink()">Copy Link</button>
</div>

<a href="/admin/panel" style="display:block;text-align:center;margin-top:16px;color:#fff">Back to Admin Panel</a>

</body>
</html>
"""

# ================= USER FUNNEL PAGE =================
@app.get("/go/{slug}", response_class=HTMLResponse)
async def ad_page(slug: str, request: Request, db=Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    key = f"{ip}:{slug}"
    now = time.time()
    if now - REQUEST_LOG.get(key, 0) < 1:
        raise HTTPException(status_code=429, detail="Too fast")
    REQUEST_LOG[key] = now

    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return HTMLResponse("Invalid link", status_code=404)
    link.clicks += 1
    db.commit()

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
let t=15;
let i=setInterval(()=>{
    document.getElementById("status").innerText = "Please wait "+t+" seconds we are loading your content";
    if(t<=0){{
        clearInterval(i);
        document.getElementById("status").innerText = "Scroll down and click Continue";
        document.getElementById("c").style.display="block";
    }}
    t--;
}},1000);
</script>
</head>
<body>

<div class="card">
<h3>Sponsored</h3>
<p id="status">Please wait 15 seconds we are loading your content</p>
</div>

<div class="card" id="c" style="display:none">
<a href="{BASE_URL}/redirect/{slug}">
<button class="btn">Continue</button>
</a>
</div>

</body>
</html>
"""

# ================= FINAL REDIRECT =================
@app.get("/redirect/{slug}")
async def final_redirect(slug: str, db=Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return RedirectResponse("/")
    link.completed += 1
    db.commit()
    return RedirectResponse(link.target)