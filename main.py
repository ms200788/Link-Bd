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
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Please wait</title>

<style>
body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: #fff;
}}

.container {{
    max-width: 420px;
    margin: auto;
    padding: 16px;
}}

.card {{
    background: #ffffff;
    color: #333;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}}

h2, h3 {{
    margin-top: 0;
}}

.timer {{
    font-size: 28px;
    font-weight: bold;
    color: #ff5722;
    text-align: center;
}}

.notice {{
    text-align: center;
    font-size: 14px;
    color: #555;
}}

.ad-box {{
    background: #f2f2f2;
    border-radius: 10px;
    padding: 10px;
    text-align: center;
    margin: 10px 0;
}}

.content p {{
    font-size: 15px;
    line-height: 1.6;
}}

#continue {{
    display: none;
    text-align: center;
}}

.btn {{
    background: linear-gradient(135deg, #ff416c, #ff4b2b);
    border: none;
    border-radius: 30px;
    padding: 14px 24px;
    color: white;
    font-size: 16px;
    cursor: pointer;
    width: 100%;
}}

.btn:active {{
    transform: scale(0.97);
}}
</style>

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

<div class="container">

    <div class="card">
        <h2>Sponsored Content</h2>

        <div class="ad-box">
            <!-- ADSTERRA BANNER CODE HERE -->
            <b>Advertisement</b>
        </div>

        <p class="notice">
            Please wait <span class="timer" id="timer">10</span> seconds  
            <br>We are loading your content…
        </p>
    </div>

    <div class="card content">
        <h3>How AI Is Changing the World</h3>

        <p>
        Artificial Intelligence (AI) is rapidly transforming the way we live,
        work, and interact with technology. From smart assistants and automated
        customer support to medical diagnostics and financial forecasting, AI
        systems are becoming deeply embedded in everyday life.
        </p>

        <p>
        Modern AI relies heavily on machine learning, where systems learn from
        vast amounts of data instead of being explicitly programmed. This allows
        AI models to recognize patterns, make predictions, and continuously
        improve over time.
        </p>

        <div class="ad-box">
            <!-- ADSTERRA VIDEO / SOCIAL BAR -->
            <b>Video Ad</b>
        </div>

        <p>
        As AI adoption grows, ethical considerations such as data privacy,
        transparency, and fairness become increasingly important. Responsible AI
        development ensures that technology benefits society without causing harm.
        </p>
    </div>

    <div class="card" id="continue">
        <p style="text-align:center;"><b>Scroll down and continue</b></p>
        <a href="/redirect/{slug}">
            <button class="btn">Continue to Content</button>
        </a>
    </div>

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