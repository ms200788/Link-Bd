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

# ================= IN-MEMORY CACHE =================
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

# ================= HEALTH (for UptimeRobot) =================
@app.get("/health")
async def health():
    return {"status": "alive"}

# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <h1>Content Gateway</h1>
    <p>This site provides gated access to content.</p>
    """

# ================= ADMIN =================
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return """
    <h2>Admin Panel</h2>
    <form method="post">
      Password:<br><input type="password" name="password"><br><br>
      Short Code:<br><input name="slug"><br><br>
      Target Link:<br><input name="target"><br><br>
      <button>Create</button>
    </form>
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
    LINK_CACHE[slug] = link
    return {"created": True, "short": f"/go/{slug}"}

# ================= PUBLIC AD PAGE =================
@app.get("/go/{slug}", response_class=HTMLResponse)
async def ad_page(slug: str, request: Request, db=Depends(get_db)):
    # --- Basic rate limiting ---
    ip = request.client.host
    now = time.time()
    last = REQUEST_LOG.get(ip, 0)
    if now - last < 1:
        raise HTTPException(status_code=429, detail="Too many requests")
    REQUEST_LOG[ip] = now

    # --- Cache first ---
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
<title>Please wait</title>
<script>
let t = 10;
function startTimer() {{
  let timer = setInterval(() => {{
    document.getElementById("timer").innerText = t;
    t--;
    if (t < 0) {{
      clearInterval(timer);
      document.getElementById("continue").style.display = "block";
    }}
  }}, 1000);
}}
window.onload = startTimer;
</script>
</head>

<body>

<h2>Sponsored Ads</h2>

<!-- ADSTERRA BANNER -->
<div>PASTE ADSTERRA BANNER CODE HERE</div>

<p>Please wait <b><span id="timer">10</span></b> seconds, we are loading your content.</p>

<!-- LONG AI CONTENT -->
<h3>How Artificial Intelligence Is Changing the World</h3>
<p>
Artificial Intelligence (AI) is transforming nearly every industry.
From healthcare diagnostics to automated customer support, AI systems
are enabling faster, smarter, and more efficient decision-making.
Machine learning models now analyze massive datasets to identify
patterns that humans simply cannot detect.
</p>

<p>
Large Language Models, such as modern conversational AI, are reshaping
how people interact with technology. These systems assist with writing,
coding, education, and research, making advanced knowledge more
accessible to everyone.
</p>

<!-- VIDEO / SOCIAL BAR -->
<div>PASTE ADSTERRA VIDEO / SOCIAL BAR CODE HERE</div>

<p>
As AI continues to evolve, ethical considerations and responsible
deployment will become increasingly important. Transparency,
fairness, and accountability must guide future AI development.
</p>

<div id="continue" style="display:none;">
  <p><b>Scroll down and click continue</b></p>
  <a href="/redirect/{slug}">
    <button>Continue</button>
  </a>
</div>

</body>
</html>
"""

# ================= FINAL REDIRECT =================
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