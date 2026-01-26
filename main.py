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
    background:#0f2027;
    color:#fff;
    font-family:system-ui;
    margin:0;
}}
.card {{
    background:#fff;
    color:#000;
    border-radius:16px;
    padding:18px;
    margin:16px;
}}
.btn {{
    background:#ff4b2b;
    color:#fff;
    border:none;
    padding:14px;
    width:100%;
    border-radius:30px;
    font-size:16px;
}}
.ad {{
    text-align:center;
    margin:22px 0;
}}
h1,h2,h3 {{
    color:#ff4b2b;
}}
p {{
    line-height:1.7;
    margin:12px 0;
}}
</style>

<script>
let t=15;
let i=setInterval(()=>{
  document.getElementById("t").innerText=t;
  if(t<=0){
    clearInterval(i);
    document.getElementById("msg").innerText="Scroll down, read the content and continue below";
    document.getElementById("c").style.display="block";
  }
  t--;
},1000);
</script>
</head>

<body>

<!-- TOP VIDEO AD -->
<div class="ad">
  <iframe width="100%" height="220"
    src="https://www.youtube.com/embed/dQw4w9WgXcQ"
    frameborder="0" allowfullscreen></iframe>

  <p id="msg">Please wait <b id="t">15</b> seconds while content loads</p>
</div>

<div class="card">
<h1>Artificial Intelligence: A Comprehensive Essay</h1>

<p>
Artificial Intelligence (AI) is one of the most transformative technologies of the modern era.
It represents the ability of machines to mimic human intelligence, including learning,
reasoning, problem-solving, perception, and decision-making. Once considered science fiction,
AI is now deeply integrated into daily life and global industries.
</p>

<h2>1. Historical Background of Artificial Intelligence</h2>
<p>
The idea of intelligent machines dates back centuries, appearing in myths, philosophy,
and early mechanical inventions. However, modern AI research formally began in 1956 at the
Dartmouth Conference. Early systems were rule-based and limited, but they laid the foundation
for future breakthroughs.
</p>
<p>
With the rise of computing power, data availability, and algorithmic improvements,
AI entered a new phase during the late 20th and early 21st centuries. Machine learning,
neural networks, and deep learning enabled AI systems to learn from data rather than
follow rigid instructions.
</p>

<!-- INLINE AD 1 -->
<div class="ad">
<script src="https://adsterra.com/your-ad-code1.js"></script>
</div>

<h2>2. Types of Artificial Intelligence</h2>
<p>
AI can be classified into three main categories based on capability:
</p>
<p><b>Narrow AI</b> performs specific tasks such as voice recognition or recommendation systems.
This is the most common form today.</p>
<p><b>General AI</b> would possess human-level intelligence across all tasks, though it remains theoretical.</p>
<p><b>Superintelligent AI</b> surpasses human intelligence entirely and raises ethical and existential concerns.</p>

<h2>3. Core Technologies Behind AI</h2>
<p>
Machine Learning enables systems to learn patterns from data. Deep Learning,
a subset of machine learning, uses neural networks inspired by the human brain.
Natural Language Processing allows machines to understand and generate human language,
while Computer Vision enables machines to interpret images and video.
</p>

<!-- INLINE AD 2 -->
<div class="ad">
<script src="https://adsterra.com/your-ad-code2.js"></script>
</div>

<h2>4. Applications of AI in Real Life</h2>
<p>
AI has revolutionized healthcare through disease detection, medical imaging, and drug discovery.
In finance, AI improves fraud detection, algorithmic trading, and risk analysis.
Education benefits from personalized learning systems and automated evaluation.
</p>
<p>
Transportation relies on AI for traffic prediction and autonomous vehicles.
E-commerce platforms use AI for product recommendations and customer insights.
Entertainment, agriculture, and cybersecurity also heavily depend on AI systems.
</p>

<h2>5. AI in Business and Industry</h2>
<p>
Businesses use AI to automate operations, optimize logistics, analyze customer behavior,
and improve decision-making. Chatbots and virtual assistants enhance customer service,
while predictive analytics improves forecasting and efficiency.
</p>

<!-- INLINE AD 3 -->
<div class="ad">
<script src="https://adsterra.com/your-ad-code3.js"></script>
</div>

<h2>6. Ethical Challenges and Risks</h2>
<p>
Despite its advantages, AI introduces ethical challenges such as data privacy,
algorithmic bias, job displacement, and lack of transparency. Biased training data
can lead to unfair outcomes, while automation may disrupt employment.
</p>
<p>
Responsible AI development requires fairness, accountability, transparency,
and strong regulatory frameworks.
</p>

<h2>7. Future of Artificial Intelligence</h2>
<p>
The future of AI holds immense promise. AI-driven smart cities, climate modeling,
precision medicine, and personalized education could significantly improve
human well-being. Collaboration between humans and AI systems will shape innovation.
</p>

<p>
However, careful governance, ethical oversight, and human-centric design
are essential to ensure AI benefits society as a whole.
</p>

<h2>8. Conclusion</h2>
<p>
Artificial Intelligence is not merely a technological advancement—it is a paradigm shift.
As AI continues to evolve, its impact will deepen across all aspects of life.
When developed responsibly, AI has the power to enhance productivity, creativity,
and global problem-solving.
</p>

<!-- END AD -->
<div class="ad">
<script src="https://adsterra.com/your-ad-code4.js"></script>
</div>

<!-- CONTINUE BUTTON (ONLY AT END) -->
<div id="c" style="display:none;margin-top:20px;">
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