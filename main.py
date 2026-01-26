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
DATABASE_URL = os.getenv("DATABASE_URL")

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

# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2 style='text-align:center'>Fast Link Gateway</h2>"

# ================= ADMIN =================
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
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
<h3>Admin Panel</h3>
<form method="post">
<input type="text" name="password" placeholder="Admin password">
<input type="url" name="target" placeholder="Target URL">
<button>Create Funnel Link</button>
</form>
</div>

</body>
</html>
"""

@app.post("/admin", response_class=HTMLResponse)
async def admin_create(
    password: str = Form(...),
    target: str = Form(...),
    db=Depends(get_db)
):
    check_admin(password)

    slug = generate_slug()
    while db.query(Link).filter(Link.slug == slug).first():
        slug = generate_slug()

    link = Link(
        slug=slug,
        target=target,
        clicks=0,
        completed=0,
        created_at=int(time.time())
    )
    db.add(link)
    db.commit()

    full_url = f"{BASE_URL}/go/{slug}"

    HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f2027;color:#fff;font-family:system-ui}
.card{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}
button{background:#4caf50;color:#fff;border:none;padding:14px;width:100%;border-radius:30px}
input{width:100%;padding:12px}
</style>
<script>
function copyLink(){
  let i=document.getElementById("l");
  i.select();
  document.execCommand("copy");
  alert("Copied");
}
</script>
</head>
<body>

<div class="card">
<h3>Link Created</h3>
<input id="l" value="{url}" readonly>
<button onclick="copyLink()">Copy Link</button>
</div>

</body>
</html>
"""
    return HTML.format(url=full_url)

# ================= AD PAGE =================
@app.get("/go/{slug}", response_class=HTMLResponse)
async def ad_page(slug: str, request: Request, db=Depends(get_db)):
    ip = request.client.host
    now = time.time()
    if now - REQUEST_LOG.get(ip, 0) < 1:
        raise HTTPException(status_code=429)
    REQUEST_LOG[ip] = now

    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return "Invalid link"

    link.clicks += 1
    db.commit()

    HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f2027;color:#fff;font-family:system-ui}
.card{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}
.btn{background:#ff4b2b;color:#fff;border:none;padding:14px;width:100%;border-radius:30px}
a{text-decoration:none}
</style>
<script>
let t=10;
let i=setInterval(()=>{
  document.getElementById("t").innerText=t;
  if(t<=0){
    clearInterval(i);
    document.getElementById("c").style.display="block";
    document.getElementById("t").innerText=0;
  }
  t--;
},1000);
</script>
</head>
<body>

<div class="card">
<h3>Sponsored</h3>
<p>Please wait <b id="t">10</b> seconds</p>
<!-- AD PLACE HERE -->
</div>

<div class="card" id="c" style="display:none">
<a href="/redirect/{slug}">
<button class="btn">Continue</button>
</a>
</div>

</body>
</html>
"""
    return HTML.format(slug=slug)

# ================= REDIRECT =================
@app.get("/redirect/{slug}")
async def final_redirect(slug: str, db=Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return RedirectResponse("/")
    link.completed += 1
    db.commit()
    return RedirectResponse(link.target)