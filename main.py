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
<title>Artificial Intelligence Explained</title>

<style>
body {{
    background:#0f2027;
    color:#fff;
    font-family:system-ui;
    margin:0;
}}
.card {{
    background:#ffffff;
    color:#000;
    border-radius:16px;
    padding:20px;
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
h1,h2,h3 {{
    color:#1e293b;
}}
p {{
    line-height:1.8;
    margin:14px 0;
}}
.timer {{
    background:#f1f5f9;
    color:#000;
    border-radius:12px;
    padding:12px;
    margin-bottom:16px;
    font-weight:500;
}}
#continueBox {{
    display:none;
    margin-top:24px;
}}
</style>

<script>
let t = 15;
let timer = setInterval(() => {{
    document.getElementById("t").innerText = t;
    if (t <= 0) {{
        clearInterval(timer);
        document.getElementById("msg").innerText = "Scroll down and continue";
        document.getElementById("continueBox").style.display = "block";
    }}
    t--;
}}, 1000);
</script>

</head>
<body>

<script src="https://pl28574839.effectivegatecpm.com/6f/6f/f2/6f6ff25ccc5d4bbef9cdeafa839743bb.js"></script>

<div class="card">

<!-- TIMER -->
<div class="timer">
<p id="msg">Please wait <b id="t">15</b> seconds while your content loads</p>
</div>

<h1>Artificial Intelligence: Understanding the Technology That Is Reshaping Humanity</h1>

<p>
Artificial Intelligence, commonly referred to as AI, is one of the most powerful and transformative
technologies ever created by humans. What once existed only in science fiction novels and futuristic
movies is now deeply integrated into our daily lives.  From smartphones and search engines to healthcare,
finance, transportation, and education, AI has become an invisible yet essential part of modern society.
</p>

<p>
At its core, artificial intelligence refers to the ability of machines to simulate human intelligence.
This includes the capacity to learn from experience, reason logically, recognize patterns, understand
language, and make decisions. Unlike traditional software programs that follow fixed instructions,
AI systems can adapt, improve, and evolve based on the data they process.
</p>

<h2>1. The Origins and History of Artificial Intelligence</h2>

<p>
The idea of intelligent machines dates back thousands of years. Ancient myths described mechanical beings
capable of thought, while philosophers debated whether intelligence could exist outside the human mind.
However, the scientific foundation of artificial intelligence began in the mid-20th century.
</p>

<p>
In 1956, a group of researchers gathered at the Dartmouth Conference, where the term “Artificial
Intelligence” was officially introduced. Early AI systems focused on rule-based logic and symbolic
reasoning. These systems could solve mathematical problems and play simple games, but they lacked
flexibility and real-world understanding.
</p>

<p>
Progress was slow due to limited computing power and data availability. However, with the rise of
powerful computers, large datasets, and improved algorithms in the late 20th and early 21st centuries,
AI experienced a resurgence. This new era introduced machine learning and deep learning, which allowed
machines to learn directly from data rather than rely on manually written rules.
</p>

<h2>2. How Artificial Intelligence Works</h2>

<p>
Artificial intelligence systems function by processing large amounts of data through algorithms
designed to identify patterns and relationships. The quality of an AI system depends heavily on the
data it is trained on, the algorithms it uses, and the computational resources available.
</p>

<p>
Machine learning is a key component of modern AI. Instead of being explicitly programmed for every
possible scenario, machine learning models learn from examples. Over time, they improve their
performance as they are exposed to more data.
</p>

<p>
Deep learning, a subset of machine learning, uses artificial neural networks inspired by the human
brain. These networks consist of layers of interconnected nodes that process information in stages.
Deep learning has enabled breakthroughs in image recognition, speech processing, and natural language
understanding.
</p>

<script async="async" data-cfasync="false" src="https://pl28575184.effectivegatecpm.com/f42c86f37946ef5ab59eb2d53980afa3/invoke.js"></script>
<div id="container-f42c86f37946ef5ab59eb2d53980afa3"></div>

<h2>3. Types of Artificial Intelligence</h2>

<p>
Artificial intelligence can be categorized into different types based on its capabilities.
</p>

<ul>
<li><b>Narrow AI:</b> Also known as weak AI, this type is designed for a specific task. Examples include
voice assistants, recommendation systems, and facial recognition software.</li>

<li><b>General AI:</b> This theoretical form of AI would have human-level intelligence across a wide
range of tasks. General AI does not yet exist but remains a major research goal.</li>

<li><b>Superintelligent AI:</b> A hypothetical form of AI that surpasses human intelligence in every
aspect. This concept raises profound ethical and philosophical questions.</li>
</ul>

<h2>4. Applications of Artificial Intelligence in Daily Life</h2>

<p>
Artificial intelligence is already embedded in everyday experiences. Smartphones use AI for facial
recognition, predictive text, and voice commands. Search engines rely on AI algorithms to deliver
relevant results. Social media platforms use AI to recommend content and detect harmful behavior.
</p>

<p>
In healthcare, AI assists doctors in diagnosing diseases, analyzing medical images, predicting patient
outcomes, and developing personalized treatment plans. AI-powered tools can detect conditions such as
cancer earlier and with greater accuracy than traditional methods.
</p>

<p>
In finance, AI helps detect fraud, manage risk, automate trading, and provide personalized financial
advice. Banks and payment systems rely on AI to monitor transactions and prevent cybercrime.
</p>

<h2>5. Artificial Intelligence in Business and Industry</h2>

<p>
Businesses across industries are adopting AI to improve efficiency and competitiveness. AI-driven
automation reduces repetitive tasks, allowing employees to focus on creative and strategic work.
Customer service chatbots provide instant responses, while predictive analytics helps businesses
anticipate demand and optimize supply chains.
</p>

<p>
Manufacturing uses AI for quality control, predictive maintenance, and process optimization.
Retailers rely on AI to personalize recommendations, manage inventory, and analyze customer behavior.
Marketing teams use AI to target audiences and measure campaign effectiveness.
</p>

<h2>6. Ethical Challenges and Social Impact of AI</h2>

<p>
Despite its benefits, artificial intelligence raises serious ethical and social concerns. One major
issue is data privacy. AI systems require vast amounts of data, often including personal information.
Ensuring that this data is collected and used responsibly is critical.
</p>

<p>
Another challenge is algorithmic bias. If an AI system is trained on biased data, it may produce unfair
or discriminatory outcomes. This can affect hiring decisions, loan approvals, law enforcement, and
other sensitive areas.
</p>

<p>
Job displacement is another concern. Automation powered by AI may replace certain jobs, particularly
those involving repetitive tasks. However, AI also creates new opportunities and professions that
require advanced skills and human creativity.
</p>

<script>
  atOptions = {
    'key' : 'a3a53ccd363dfab580fb6f222586ae7b',
    'format' : 'iframe',
    'height' : 250,
    'width' : 300,
    'params' : {}
  };
</script>
<script src="https://www.highperformanceformat.com/a3a53ccd363dfab580fb6f222586ae7b/invoke.js"></script>

<h2>7. The Role of AI in Education</h2>

<p>
Artificial intelligence has the potential to transform education by enabling personalized learning.
AI-powered systems can adapt content to individual learning styles, track progress, and provide
instant feedback. Teachers can use AI tools to identify students who need additional support.
</p>

<p>
Online learning platforms use AI to recommend courses, analyze engagement, and improve learning
outcomes. While AI cannot replace human educators, it can enhance teaching effectiveness and
expand access to quality education.
</p>

<h2>8. The Future of Artificial Intelligence</h2>

<p>
The future of artificial intelligence holds immense promise. AI is expected to play a major role
in addressing global challenges such as climate change, disease prevention, and resource management.
Smart cities powered by AI could improve transportation, energy efficiency, and public safety.
</p>

<p>
Human-AI collaboration will become increasingly important. Rather than replacing humans, AI is
likely to augment human capabilities, enabling people to work more efficiently and creatively.
</p>

<p>
However, the future of AI depends on responsible development, ethical governance, and global
cooperation. Ensuring that AI benefits humanity as a whole requires thoughtful regulation,
transparency, and public awareness.
</p>

<h2>9. Conclusion</h2>

<p>
Artificial intelligence is more than just a technological innovation; it represents a fundamental
shift in how humans interact with machines and information.
</p>

<p>
Understanding AI is no longer optional—it is essential for navigating the future.
</p>

<script>
  atOptions = {
    'key' : '32b56ec2e176097bcb57ac54cb139aa2',
    'format' : 'iframe',
    'height' : 50,
    'width' : 320,
    'params' : {}
  };
</script>
<script src="https://www.highperformanceformat.com/32b56ec2e176097bcb57ac54cb139aa2/invoke.js"></script>


<!-- CONTINUE BUTTON (APPEARS AFTER TIMER) -->
<div id="continueBox">
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