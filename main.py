import os
import time
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# ================= CONFIG =================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DB SETUP =================
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True)
    target = Column(String)

Base.metadata.create_all(bind=engine)

# ================= APP =================
app = FastAPI()

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
def health():
    return {"status": "alive"}

# ================= ADMIN =================
@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return """
    <h2>Admin Panel</h2>
    <form method="post">
      Password: <input type="password" name="password"><br><br>
      Short Code: <input name="slug"><br><br>
      Target Link: <input name="target"><br><br>
      <button>Create</button>
    </form>
    """

@app.post("/admin")
def admin_create(
    password: str = Form(...),
    slug: str = Form(...),
    target: str = Form(...),
    db=Depends(get_db)
):
    check_admin(password)
    link = Link(slug=slug, target=target)
    db.add(link)
    db.commit()
    return {"status": "created", "short": f"/go/{slug}"}

# ================= PUBLIC FLOW =================
@app.get("/go/{slug}", response_class=HTMLResponse)
def ad_page(slug: str, db=Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return "Invalid link"

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
<h2>Ads</h2>

<!-- ADSTERRA AD PLACEHOLDER -->
<div>AD SLOT 1</div>
<div>AD SLOT 2</div>

<p>Please wait <span id="timer">10</span> seconds, we are loading your content.</p>

<div style="height:300px">
<p>
AI is transforming industries worldwide. From automation to personalization,
modern systems rely on machine learning, large language models, and cloud computing.
This page simulates long-form content to increase engagement and session time.
</p>
</div>

<!-- VIDEO AD PLACEHOLDER -->
<div>VIDEO AD HERE</div>

<div id="continue" style="display:none;">
  <a href="/redirect/{slug}"><button>Continue</button></a>
</div>

</body>
</html>
"""

@app.get("/redirect/{slug}")
def final_redirect(slug: str, db=Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return RedirectResponse("/")
    return RedirectResponse(link.target)
