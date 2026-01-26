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
ADMIN_COOKIE = "admin_session"

# ================= HELPERS =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_admin_cookie(request: Request):
    cookie = request.cookies.get(ADMIN_COOKIE)
    if cookie != "true":
        raise HTTPException(status_code=403, detail="Forbidden: Admin only")

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

# ================= ADMIN LOGIN =================
@app.get("/admin", response_class=HTMLResponse)
async def admin_login():
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
<input type="password" name="password" placeholder="Admin password">
<button>Login</button>
</form>
</div>

</body>
</html>
"""

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_do_login(password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Forbidden: Wrong password")
    # Set cookie and redirect to admin panel
    response = RedirectResponse("/admin/panel", status_code=302)
    response.set_cookie(key=ADMIN_COOKIE, value="true", max_age=86400, httponly=False)
    return response

# ================= ADMIN PANEL =================
@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, db=Depends(get_db)):
    check_admin_cookie(request)
    links = db.query(Link).all()
    links_html = ""
    for link in links:
        links_html += f"<tr><td>{link.slug}</td><td>{link.target}</td><td>{link.clicks}</td><td>{link.completed}</td></tr>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0f2027;color:#fff;font-family:system-ui}}
.card{{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}}
input,button{{width:100%;padding:12px;margin-top:8px;border-radius:12px}}
button{{background:#4caf50;color:#fff;border:none;padding:12px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;border:1px solid #000;text-align:center}}
</style>
</head>
<body>

<div class="card">
<h3>Create Funnel Link</h3>
<form method="post" action="/admin/create">
<input type="url" name="target" placeholder="Target URL" required>
<button>Create Funnel Link</button>
</form>
</div>

<div class="card">
<h3>All Links Stats</h3>
<table>
<tr><th>Slug</th><th>Target</th><th>Clicks</th><th>Completed</th></tr>
{links_html}
</table>
</div>

</body>
</html>
"""

@app.post("/admin/create", response_class=HTMLResponse)
async def admin_create(request: Request, target: str = Form(...), db=Depends(get_db)):
    check_admin_cookie(request)

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
<title>Artificial Intelligence Essay</title>
<style>
body {{
    background: #0f2027;
    color: #fff;
    font-family: system-ui;
    margin: 0;
    padding: 0;
}}
.card {{
    background: #fff;
    color: #000;
    border-radius: 16px;
    padding: 16px;
    margin: 16px;
}}
.btn {{
    background: #ff4b2b;
    color: #fff;
    border: none;
    padding: 14px;
    width: 100%;
    border-radius: 30px;
    cursor: pointer;
    font-size: 16px;
}}
.ad-container {{
    text-align: center;
    margin: 20px 0;
}}
h1, h2, h3 {{
    color: #ff4b2b;
    margin-top: 20px;
}}
p, li {{
    margin: 10px 0;
    line-height: 1.6;
}}
</style>
<script>
let t = 15;
let i = setInterval(() => {{
  document.getElementById("t").innerText = t;
  if(t <= 0){{
    clearInterval(i);
    document.getElementById("msg").innerText = "You can now scroll through the essay and click Continue at the end";
    document.getElementById("c").style.display="block";
  }}
  t--;
}}, 1000);
</script>
</head>
<body>

<!-- Top Video Ad -->
<div class="ad-container">
    <h3>Sponsored Video</h3>
    <iframe width="100%" height="200" src="https://www.youtube.com/embed/dQw4w9WgXcQ" 
        title="Ad Video" frameborder="0" allowfullscreen></iframe>
    <p id="msg">Please wait <b id="t">15</b> seconds we are loading your content</p>
</div>

<!-- AI Essay Card -->
<div class="card">
    <h1>Artificial Intelligence: Transforming the Modern World</h1>

    <p>
        Artificial Intelligence (AI) is no longer a concept confined to science fiction. 
        Today, AI is a driving force behind countless technological advancements that shape 
        industries, economies, and daily life. This essay explores the multifaceted world 
        of AI, its history, applications, challenges, and future prospects.
    </p>

    <h2>1. History and Evolution of AI</h2>
    <p>
        The concept of AI dates back to ancient times when myths and stories envisioned machines 
        capable of human-like thinking. The formal field of AI research began in 1956 at a 
        conference at Dartmouth College. Early AI systems were rule-based, relying on logic 
        and simple problem-solving strategies. Over the decades, advances in computing power 
        and algorithms enabled the development of machine learning, neural networks, and 
        natural language processing, forming the foundation of modern AI systems.
    </p>

    <!-- Inline Ad -->
    <div class="ad-container">
        <script type="text/javascript" src="https://adsterra.com/your-ad-code1.js"></script>
    </div>

    <h2>2. Types of AI</h2>
    <p>
        AI can be broadly categorized into three types: narrow AI, general AI, and superintelligent AI.
    </p>
    <ul>
        <li><strong>Narrow AI:</strong> Also known as weak AI, this type is specialized for a single task, 
        such as speech recognition, recommendation engines, or autonomous driving assistance.</li>
        <li><strong>General AI:</strong> Also called strong AI, it can perform any intellectual task that a human can do. 
        General AI is still largely theoretical and remains a long-term goal.</li>
        <li><strong>Superintelligent AI:</strong> A hypothetical AI that surpasses human intelligence in all areas. 
        Ethical considerations and control mechanisms are critical when discussing superintelligence.</li>
    </ul>

    <!-- Inline Ad -->
    <div class="ad-container">
        <script type="text/javascript" src="https://adsterra.com/your-ad-code2.js"></script>
    </div>

    <h2>3. Applications of AI</h2>
    <p>
        AI impacts nearly every industry and sector. In healthcare, AI assists in diagnosing diseases, predicting 
        patient outcomes, and even developing personalized treatment plans. In finance, AI algorithms detect 
        fraudulent transactions, automate trading, and optimize investment strategies. Autonomous vehicles, 
        smart home devices, virtual assistants, and content recommendation engines are all powered by AI.
    </p>

    <p>
        AI also plays a crucial role in scientific research, enabling simulations, data analysis, and pattern 
        recognition at scales impossible for humans. It enhances efficiency, reduces human error, and allows 
        for innovative solutions to complex problems.
    </p>

    <!-- Inline Ad -->
    <div class="ad-container">
        <script type="text/javascript" src="https://adsterra.com/your-ad-code3.js"></script>
    </div>

    <h2>4. Machine Learning and Deep Learning</h2>
    <p>
        Machine Learning (ML) is a subset of AI that enables systems to learn from data rather than follow 
        explicit programming instructions. ML algorithms analyze patterns and make predictions or decisions 
        based on input data. Deep Learning, a subset of ML, uses artificial neural networks to process complex 
        data such as images, video, and natural language. These technologies power applications like facial 
        recognition, autonomous driving, and language translation.
    </p>

    <h2>5. Ethical Considerations</h2>
    <p>
        While AI offers tremendous benefits, it also raises ethical concerns. Issues include algorithmic bias, 
        data privacy, job displacement, and transparency. Responsible AI development requires frameworks 
        that ensure fairness, accountability, and alignment with human values.
    </p>

    <h2>6. Future Prospects</h2>
    <p>
        The future of AI promises revolutionary changes. Smart cities, climate modeling, personalized education, 
        and advanced healthcare systems are some areas where AI could make profound impacts. Collaboration 
        between humans and AI, along with ethical oversight, will determine the trajectory of AI in society.
    </p>

    <p>
        In conclusion, AI is transforming the modern world, offering unprecedented opportunities while 
        presenting complex challenges. Responsible development, ethical considerations, and innovative 
        applications will define how AI shapes our future.
    </p>

    <!-- End Ad -->
    <div class="ad-container">
        <script type="text/javascript" src="https://adsterra.com/your-ad-code4.js"></script>
    </div>

    <!-- Continue Button -->
    <div id="c" style="display:none; margin-top:16px;">
        <a href="{BASE_URL}/redirect/{slug}">
            <button class="btn">Continue</button>
        </a>
    </div>
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