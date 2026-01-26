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
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Artificial Intelligence Explained</title>

<style>
body {
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: #ffffff;
}

.container {
    max-width: 480px;
    margin: auto;
    padding: 14px;
}

.card {
    background: #ffffff;
    color: #222;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 16px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
}

h1, h2, h3 {
    margin-top: 0;
    color: #111;
}

p {
    font-size: 15px;
    line-height: 1.7;
}

ul {
    padding-left: 18px;
}

li {
    margin-bottom: 8px;
}

img {
    width: 100%;
    border-radius: 14px;
    margin: 12px 0;
}

.ad-box {
    background: #f2f2f2;
    border-radius: 14px;
    padding: 14px;
    text-align: center;
    margin: 16px 0;
    color: #444;
    font-size: 14px;
}

.ad-box b {
    display: block;
    margin-bottom: 6px;
}

</style>
</head>

<body>

<div class="container">

<!-- INTRO -->
<div class="card">
<h1>Artificial Intelligence (AI) Explained</h1>

<p>
Artificial Intelligence, commonly known as <b>AI</b>, is one of the most
important technologies of the modern world. It allows machines to think,
learn, and make decisions similar to humans.
</p>

<p>
From smartphones and social media to healthcare and space exploration,
AI is everywhere. In this article, we will explore AI in a very simple
and easy way so anyone can understand it.
</p>

<img src="https://images.unsplash.com/photo-1677442136019-21780ecad995" alt="AI Technology">
</div>

<!-- AD PLACE 1 -->
<div class="ad-box">
<b>Advertisement</b>
PASTE ADSTERRA BANNER CODE HERE
</div>

<!-- WHAT IS AI -->
<div class="card">
<h2>What is Artificial Intelligence?</h2>

<p>
Artificial Intelligence is the ability of a machine or computer system
to perform tasks that normally require human intelligence.
</p>

<ul>
<li>Understanding language</li>
<li>Recognizing images and faces</li>
<li>Learning from experience</li>
<li>Solving problems</li>
<li>Making decisions</li>
</ul>

<p>
AI systems are trained using data. The more data they get, the smarter
they become.
</p>
</div>

<!-- AI FIELDS -->
<div class="card">
<h2>Major Fields of Artificial Intelligence</h2>

<img src="https://images.unsplash.com/photo-1581092334651-ddf26d9a09d0" alt="AI Fields">

<h3>1. Machine Learning</h3>
<p>
Machine Learning allows computers to learn from data without being
explicitly programmed.
</p>

<h3>2. Deep Learning</h3>
<p>
Deep Learning uses neural networks inspired by the human brain.
It is used in voice assistants and image recognition.
</p>

<h3>3. Natural Language Processing (NLP)</h3>
<p>
NLP helps machines understand human language.
Examples include chatbots and translation apps.
</p>

<h3>4. Computer Vision</h3>
<p>
This field allows machines to see and understand images and videos.
</p>
</div>

<!-- AD PLACE 2 -->
<div class="ad-box">
<b>Advertisement</b>
PASTE ADSTERRA VIDEO / SOCIAL BAR CODE HERE
</div>

<!-- AI EFFECTS -->
<div class="card">
<h2>Effects of AI on Society</h2>

<p>
AI has changed how we live and work. It has both positive and negative
effects.
</p>

<h3>Positive Effects</h3>
<ul>
<li>Faster work and automation</li>
<li>Better medical diagnosis</li>
<li>Smart assistants and helpers</li>
<li>Improved education</li>
</ul>

<h3>Challenges</h3>
<ul>
<li>Job displacement</li>
<li>Privacy concerns</li>
<li>Bias in AI systems</li>
<li>Over-dependence on machines</li>
</ul>
</div>

<!-- MODERNIZATION -->
<div class="card">
<h2>AI and Modernization</h2>

<img src="https://images.unsplash.com/photo-1581093588401-22d8c3c21b57" alt="AI Modernization">

<p>
AI is driving modernization across industries.
</p>

<ul>
<li>Smart cities with traffic control</li>
<li>AI-powered healthcare systems</li>
<li>Online learning platforms</li>
<li>Self-driving vehicles</li>
<li>Automated factories</li>
</ul>

<p>
Modern businesses use AI to analyze customers, predict trends,
and increase profits.
</p>
</div>

<!-- AD PLACE 3 -->
<div class="ad-box">
<b>Advertisement</b>
PASTE ADSTERRA NATIVE AD HERE
</div>

<!-- FUTURE -->
<div class="card">
<h2>The Future of Artificial Intelligence</h2>

<p>
The future of AI is both exciting and uncertain.
Experts believe AI will become more intelligent and helpful.
</p>

<h3>Future Possibilities</h3>
<ul>
<li>AI doctors and surgeons</li>
<li>Fully autonomous vehicles</li>
<li>Personal AI assistants for everyone</li>
<li>Advanced robotics</li>
<li>AI in space exploration</li>
</ul>

<p>
However, ethical AI development is very important.
Humans must control AI and use it responsibly.
</p>
</div>

<!-- FINAL -->
<div class="card">
<h2>Conclusion</h2>

<p>
Artificial Intelligence is not science fiction anymore.
It is already shaping our present and future.
</p>

<p>
When used wisely, AI can improve lives, solve global problems,
and create a better world for everyone.
</p>

<p>
Learning about AI today prepares us for tomorrow.
</p>
</div>

</div>

</body>
</html>

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