import os
import random
import string
import urllib.request
import urllib.parse
import json
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

# ================= CONFIG =================

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
BASE_URL = os.getenv("BASE_URL", "https://your-domain.com")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")  # Your Telegram numeric ID

DATABASE_FILE = "database.txt"

app = FastAPI()
ADMIN_COOKIE = "admin_session"

# ================= UTILITIES =================

def generate_slug(length=8):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def generate_token(length=12):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def save_funnel(slug, token, target):
    with open(DATABASE_FILE, "a") as f:
        f.write(f"{slug}|{token}|{target}\n")

def get_funnel(slug):
    if not os.path.exists(DATABASE_FILE):
        return None

    with open(DATABASE_FILE, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 3 and parts[0] == slug:
                return {
                    "slug": parts[0],
                    "token": parts[1],
                    "target": parts[2]
                }
    return None

def check_admin(request: Request):
    if request.cookies.get(ADMIN_COOKIE) != "true":
        raise HTTPException(status_code=403)

# ================= TELEGRAM BOT (OWNER ONLY) =================

def send_message(chat_id, text):
    if not BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode()

    req = urllib.request.Request(url, data=data)
    urllib.request.urlopen(req)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    user_id = str(message["from"]["id"])
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")

    # 🔒 Only owner can create funnel
    if user_id != OWNER_ID:
        send_message(chat_id, "❌ Not authorized.")
        return {"ok": True}

    if text.startswith("/create "):
        target = text.replace("/create ", "").strip()

        slug = generate_slug()
        while get_funnel(slug):
            slug = generate_slug()

        token = generate_token()

        save_funnel(slug, token, target)

        full_link = f"{BASE_URL}/{slug}"

        send_message(chat_id, f"✅ Funnel Created:\n{full_link}")

    return {"ok": True}

# ================= HOME =================

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2 style='text-align:center'>Fast Link Gateway Running</h2>"

# ================= ADMIN LOGIN =================

@app.get("/admin", response_class=HTMLResponse)
async def admin_login():
    return """
    <div style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif">
        <form method="post" action="/admin/login" style="width:320px">
            <h3>Admin Login</h3>
            <input type="password" name="password" placeholder="Password"
            style="width:100%;padding:12px;margin:10px 0">
            <button style="width:100%;padding:12px">Login</button>
        </form>
    </div>
    """

@app.post("/admin/login")
async def admin_do_login(password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403)

    response = RedirectResponse("/admin/panel", status_code=302)
    response.set_cookie(key=ADMIN_COOKIE, value="true", max_age=86400, httponly=True)
    return response

# ================= ADMIN PANEL =================

@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request):
    check_admin(request)

    return """
    <div style="max-width:500px;margin:auto;padding:20px;font-family:sans-serif">
        <h2>Create Funnel</h2>
        <form method="post" action="/admin/create">
            <input type="url" name="target" placeholder="Target URL" required
            style="width:100%;padding:12px;margin-bottom:12px">
            <button style="width:100%;padding:12px">Create</button>
        </form>
    </div>
    """

@app.post("/admin/create", response_class=HTMLResponse)
async def admin_create(request: Request, target: str = Form(...)):
    check_admin(request)

    slug = generate_slug()
    while get_funnel(slug):
        slug = generate_slug()

    token = generate_token()

    save_funnel(slug, token, target)

    full_link = f"{BASE_URL}/{slug}"

    return f"""
    <div style="max-width:500px;margin:auto;padding:20px;font-family:sans-serif">
        <h3>Link Created</h3>
        <input id="linkBox" value="{full_link}" readonly
        style="width:100%;padding:10px;margin-bottom:10px">
        <button onclick="copyLink()" style="width:100%;padding:10px">Copy</button>
        <br><br>
        <a href="/admin/panel">Back</a>
    </div>

    <script>
    function copyLink() {{
        var copyText = document.getElementById("linkBox");
        copyText.select();
        document.execCommand("copy");
        alert("Copied!");
    }}
    </script>
    """

# ================= USER AD PAGE =================

@app.get("/{slug}", response_class=HTMLResponse)
async def user_page(slug: str):

    data = get_funnel(slug)

    if not data:
        return HTMLResponse("Invalid link", status_code=404)

    token = data["token"]

    return f"""
        <!DOCTYPE html>
<html lang="en">  
<head>  
<meta charset="UTF-8">  
<title>Machine Learning and Deep Learning in Artificial Intelligence</title>  
<meta name="viewport" content="width=device-width, initial-scale=1.0">  

<style>
body {{
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.8;
    margin: 0;
    background-color: #0f2027;
    color: #eaeaea;
}}

h2, h3, h4 {{ color: #4da3ff; }}
h1 {{ color: #121212 }}

ul {{ margin-left: 25px; }}

.section {{
    background: #ffffff;
    padding: 25px;
    margin-bottom: 30px;
    border-left: 6px solid #4da3ff;
}}

.card {{
    background:#ffffff;
    color:#000000;
    border-radius:16px;
    padding:20px;
    margin:16px;
}}

p {{
    line-height:1.8;
    margin:14px 0;
    font-size:15px;
}}

.btn {{
    background:#ffffff;
    color:#4da3ff;
    border:none;
    padding:14px;
    width:100%;
    border-radius:30px;
    font-size:16px;
}}

.timer {{
    text-align:center;
    font-size:16px;
    margin:20px 0;
}}

.ad {{
    margin:24px 0;
    text-align:center;
}}

.conclusion {{
    background:#f0f3ff;
    padding:20px;
    border-left:5px solid #4a63ff;
    border-radius:12px;
}}

.topbar {{
    background: #121212;
    color: #fff;
    padding: 12px 16px;
    font-size: 20px;
    font-weight: 700;
}}
</style>

<script>
let timerDone = false;
let verified = false;

// ================= TIMER =================
function startTimer() {{
    let t = 20;

    let timer = setInterval(() => {{
        document.getElementById("t").innerText = t;

        if (t <= 0) {{
            clearInterval(timer);
            timerDone = true;
            document.getElementById("timerText").innerText = "Please verify to continue";
            document.getElementById("verifyBox").style.display = "block";
            checkUnlock();
        }}

        t--;
    }}, 1000);
}}

window.onload = function() {{
    startTimer();
}};

// ================= VERIFY =================
function verifyNow() {{
    if (verified) return;
    verified = true;

    window.open("https://mlinks-pgds.onrender.com/go/NVDOEC", "_blank");

    document.getElementById("verifyBox").style.display = "none";

    checkUnlock();
}}

// ================= UNLOCK =================
function checkUnlock() {{
    if (timerDone && verified) {{
        document.getElementById("continueBox").style.display = "block";
    }}
}}
</script>
</head>

<body>

<script src="https://pl28574839.effectivegatecpm.com/6f/6f/f2/6f6ff25ccc5d4bbef9cdeafa839743bb.js"></script>

<div class="topbar">𝘼𝙄 - 𝙈𝙇 & 𝘿𝙇</div>

<div class="card">

<h1>Machine Learning (ML) and Deep Learning (DL) in Artificial Intelligence</h1>

<div class="timer">
<p id="timerText">Please wait <b id="t">20</b> seconds while content loads</p>
</div>

<div class="section"><h2>Introduction</h2>

<p>
Artificial Intelligence (AI) is one of the most revolutionary fields of computer science in the modern era.
It focuses on creating intelligent machines that can perform tasks which normally require human intelligence.
These tasks include thinking, learning, reasoning, decision-making, problem-solving, speech recognition,
and visual perception. With the rapid growth of technology and data, AI has become an important part of
our daily lives.
</p>

<p>
When we use Google search, YouTube recommendations, face unlock on smartphones, voice assistants like
Alexa or Siri, or online shopping suggestions, we are directly interacting with Artificial Intelligence.
Among the various branches of AI, <b>Machine Learning (ML)</b> and <b>Deep Learning (DL)</b> are the most
important and widely used.
</p>

<p>
Machine Learning allows computers to learn from data and improve their performance without being explicitly
programmed. Deep Learning, on the other hand, is an advanced form of Machine Learning that uses artificial
neural networks inspired by the human brain. These technologies are transforming industries such as
education, healthcare, finance, transportation, and entertainment.
</p>

<p>
This document explains Machine Learning and Deep Learning in detail, using simple language suitable
for Class 12 students and senior learners. It also covers applications, advantages, limitations,
differences, and future scope, providing a complete understanding of the topic.
</p>
</div>

<div class="section"><h2>Artificial Intelligence: An Overview</h2>

<p>
Artificial Intelligence is the science and engineering of making intelligent machines. The main idea
behind AI is to simulate human intelligence in machines so that they can think and act like humans.
AI systems can be designed to perform specific tasks or to behave in a general intelligent manner.
</p>

<h3>Main characteristics of Artificial Intelligence:</h3>
<ul>
    <li>Ability to learn from experience</li>
    <li>Ability to reason and solve problems</li>
    <li>Ability to understand language</li>
    <li>Ability to recognize patterns</li>
    <li>Ability to make decisions</li>
</ul>

<p>
Artificial Intelligence can be broadly divided into the following categories:
</p>

<ul>
    <li><b>Narrow AI:</b> Designed to perform a specific task (e.g., chatbots, recommendation systems)</li>
    <li><b>General AI:</b> Can perform any intellectual task that a human can do (still under research)</li>
    <li><b>Super AI:</b> Intelligence that surpasses human intelligence (theoretical concept)</li>
</ul>

<p>
Machine Learning and Deep Learning mainly fall under Narrow AI, but they are continuously evolving
towards more advanced intelligence.
</p>
</div>

<div class="ad">
<script async="async" data-cfasync="false"
src="https://pl28575184.effectivegatecpm.com/f42c86f37946ef5ab59eb2d53980afa3/invoke.js"></script>
<div id="container-f42c86f37946ef5ab59eb2d53980afa3"></div>
</div>

<div class="section"><h2>Machine Learning (ML)</h2>

<h3>Definition of Machine Learning</h3>

<p>
Machine Learning is a subset of Artificial Intelligence that focuses on developing systems that can
learn from data and improve their performance automatically. Instead of following fixed rules,
Machine Learning models analyze data, identify patterns, and make decisions based on learned knowledge.
</p>

<p>
In simple words, Machine Learning is teaching a computer to learn from examples, just like humans learn
from their experiences.
</p>

<h3>Why Machine Learning is Important</h3>

<p>
In today’s digital world, huge amounts of data are generated every second. It is impossible for humans
to manually analyze such massive data. Machine Learning helps in processing large datasets efficiently
and extracting useful information from them.
</p>

<h4>Importance of Machine Learning:</h4>
<ul>
    <li>Handles large amounts of data efficiently</li>
    <li>Improves accuracy over time</li>
    <li>Reduces human effort</li>
    <li>Helps in making predictions</li>
    <li>Automates decision-making</li>
</ul>

<h3>How Machine Learning Works</h3>

<p>
Machine Learning systems work by using algorithms that analyze data and learn from it. The learning
process involves feeding data to the model, training it, and testing its performance.
</p>

<ul>
    <li>Data collection from reliable sources</li>
    <li>Data preprocessing and cleaning</li>
    <li>Feature selection</li>
    <li>Model training</li>
    <li>Testing and evaluation</li>
    <li>Prediction and deployment</li>
</ul>

<h3>Types of Machine Learning</h3>

<h4>1. Supervised Learning</h4>
<p>
Supervised learning uses labeled data, where both input and output are known. The model learns by comparing
its predictions with actual results.
</p>

<ul>
    <li>Example: Predicting student marks</li>
    <li>Example: Email spam classification</li>
</ul>

<h4>2. Unsupervised Learning</h4>
<p>
Unsupervised learning works with unlabeled data. The model identifies patterns and relationships without
human guidance.
</p>

<ul>
    <li>Example: Market segmentation</li>
    <li>Example: Grouping similar products</li>
</ul>

<h4>3. Reinforcement Learning</h4>
<p>
Reinforcement learning involves learning through trial and error. The system receives rewards or penalties
based on actions.
</p>

<ul>
    <li>Example: Game-playing AI</li>
    <li>Example: Robotics</li>
</ul>

<h3>Applications of Machine Learning</h3>

<ul>
    <li>Recommendation systems (Netflix, Amazon)</li>
    <li>Fraud detection</li>
    <li>Medical diagnosis</li>
    <li>Speech recognition</li>
    <li>Weather prediction</li>
    <li>Customer behavior analysis</li>
</ul>
</div>

<div class="section"><h2>Deep Learning (DL)</h2>

<h3>Definition of Deep Learning</h3>

<p>
Deep Learning is an advanced subset of Machine Learning that uses artificial neural networks with
multiple layers. These networks are inspired by the structure and functioning of the human brain.
</p>

<p>
Deep Learning is especially useful for handling unstructured data such as images, videos, audio,
and text.
</p>

<h3>Artificial Neural Networks</h3>

<p>
Neural networks consist of interconnected nodes called neurons. Each neuron processes information
and passes it to the next layer.
</p>

<ul>
    <li>Input Layer</li>
    <li>Hidden Layers</li>
    <li>Output Layer</li>
</ul>

<p>
The presence of multiple hidden layers makes the network “deep”, allowing it to learn complex patterns.
</p>

<h3>Working of Deep Learning</h3>

<p>
Deep Learning models learn by adjusting weights using a process called backpropagation. Large datasets
and high computational power are required for effective learning.
</p>

<h3>Applications of Deep Learning</h3>

<ul>
    <li>Face recognition systems</li>
    <li>Voice assistants</li>
    <li>Autonomous vehicles</li>
    <li>Medical image analysis</li>
    <li>Natural language processing</li>
</ul>
</div>

<div class="section"><h2>Difference Between Machine Learning and Deep Learning</h2>

<ul>
    <li>Machine Learning uses simpler models</li>
    <li>Deep Learning uses neural networks</li>
    <li>ML requires manual feature extraction</li>
    <li>DL performs automatic feature extraction</li>
    <li>ML needs less data</li>
    <li>DL needs large datasets</li>
</ul>
</div>

<div class="section"><h2>Advantages and Limitations</h2>

<h3>Advantages</h3>
<ul>
    <li>Automation of tasks</li>
    <li>High efficiency</li>
    <li>Improved accuracy</li>
    <li>Time-saving</li>
</ul>

<h3>Limitations</h3>
<ul>
    <li>High data dependency</li>
    <li>Computational cost</li>
    <li>Complexity</li>
    <li>Lack of emotional intelligence</li>
</ul>
</div>

<div class="section"><h2>Future Scope of ML and DL</h2>

<p>
Machine Learning and Deep Learning have a promising future. These technologies will continue to
impact every industry and create new job opportunities.
</p>

<ul>
    <li>Smart education systems</li>
    <li>Advanced healthcare</li>
    <li>Intelligent transportation</li>
    <li>Human–AI collaboration</li>
</ul>
</div>

<div class="conclusion"><h2>Conclusion</h2>

<p>
Machine Learning and Deep Learning are powerful technologies that form the foundation of modern
Artificial Intelligence. They enable machines to learn from data, identify patterns, and make
intelligent decisions. Machine Learning focuses on learning from structured data, while Deep
Learning excels in handling complex and unstructured data.
</p>

<p>
For students, understanding ML and DL is essential as these fields are shaping the future of
technology. Learning these concepts at the school level provides a strong base for higher studies
and careers in Artificial Intelligence, data science, and related fields.
</p>

<p>
In conclusion, Machine Learning and Deep Learning are not only shaping the future but are already
transforming the present world in remarkable ways.
</p>
</div>
</div>

<div id="verifyBox" style="display:none; margin:16px;">
<button class="btn" onclick="verifyNow()">Verify to Continue</button>
</div>

<div id="continueBox" style="display:none; margin:16px;">
<a href="{BASE_URL}/redirect/{slug}">
<button class="btn">Continue</button>
</a>
</div>

<script src="https://pl28576073.effectivegatecpm.com/21/83/07/218307bd8e87e8259e74f98d02f716c1.js"></script>

</body>
</html>
"""

# ================= FINAL SECURE REDIRECT =================

@app.get("/{token}/{slug}")
async def final_redirect(token: str, slug: str):

    data = get_funnel(slug)

    if not data:
        return RedirectResponse("/")

    if data["token"] != token:
        return RedirectResponse("/")

    return RedirectResponse(data["target"])