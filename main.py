"""
وكيل ذكاء اصطناعي بسيط لكن حقيقي — جاهز لـ Cloud Run.

- يستخدم Vertex AI عبر google-genai (لا يحتاج مفتاح API: مصادقة تلقائية بحساب الخدمة)
- أداة (tool) حقيقية + استدعاء تلقائي للدوال = سلوك وكيل، لا مجرد دردشة
- نقاط النهاية:  GET /  (واجهة اختبار) | GET /healthz | POST /chat
"""
import logging
import os

from flask import Flask, jsonify, request
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agent")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
MODEL_ID = os.environ.get("MODEL_ID", "gemini-2.5-flash")

if not PROJECT_ID:
    # فشل صريح عند الإقلاع أبسط بكثير من فشل غامض عند أول طلب
    raise RuntimeError("GOOGLE_CLOUD_PROJECT غير مضبوط — مرّره عبر --set-env-vars")

app = Flask(__name__)

# عميل واحد يُعاد استخدامه بين الطلبات (بدء تشغيل أسرع)
client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)

SYSTEM_INSTRUCTION = (
    "أنت وكيل ذكاء اصطناعي مساعد. أجب بإيجاز ووضوح بالعربية إن كان السؤال بالعربية. "
    "استخدم الأدوات المتاحة عند الحاجة بدل تخمين الأرقام أو البيانات."
)


# ---------- الأدوات التي يستطيع الوكيل استدعاءها ----------
def get_weather(city: str) -> dict:
    """يرجع حالة الطقس لمدينة. أداة تجريبية.

    Args:
        city: اسم المدينة.
    """
    demo = {"الجزائر": (24, "مشمس"), "قسنطينة": (21, "غائم جزئيًا"), "وهران": (26, "صافٍ")}
    temp, cond = demo.get(city, (22, "بيانات تجريبية"))
    return {"city": city, "temperature_c": temp, "condition": cond}


def add_numbers(a: float, b: float) -> dict:
    """يجمع رقمين ويعيد الناتج. أداة تجريبية.

    Args:
        a: العدد الأول.
        b: العدد الثاني.
    """
    return {"sum": a + b}


TOOLS = [get_weather, add_numbers]


# ---------- نقاط النهاية ----------
@app.get("/health")
def health():
    """فحص صحة — يستخدمه Cloud Run والمراقبة.

    ملاحظة: المسار /healthz محجوز في طبقة Google أمام Cloud Run ويرجع 404،
    لذا نستخدم /health هنا (/healthz مُبقى كاسم بديل لا يضر).
    """
    return jsonify({"ok": True, "model": MODEL_ID, "project": PROJECT_ID, "region": REGION})


@app.get("/healthz")
def health_alias():
    return health()


@app.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "الحقل 'message' مطلوب"}), 400

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
                tools=TOOLS,  # استدعاء تلقائي للدوال
            ),
        )
        return jsonify({"reply": response.text, "model": MODEL_ID})
    except Exception as exc:  # noqa: BLE001
        log.exception("فشل توليد الرد")
        return jsonify({"error": str(exc)}), 500


@app.get("/")
def index():
    return HTML_PAGE


HTML_PAGE = """<!doctype html>
<html lang="ar" dir="rtl">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>وكيل DeepSeek Agent</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, "Segoe UI", Tahoma, sans-serif; max-width: 760px;
         margin: 0 auto; padding: 24px 16px; line-height: 1.7; }
  h1 { font-size: 1.25rem; margin: 0 0 4px; }
  .sub { opacity: .65; font-size: .85rem; margin-bottom: 20px; }
  #log { border: 1px solid #8883; border-radius: 12px; padding: 14px; min-height: 260px;
         max-height: 60vh; overflow-y: auto; background: #8881; }
  .msg { margin: 8px 0; padding: 10px 12px; border-radius: 10px; white-space: pre-wrap; }
  .user { background: #2563eb22; }
  .bot  { background: #16a34a22; }
  .err  { background: #dc262622; }
  form { display: flex; gap: 8px; margin-top: 14px; }
  input { flex: 1; padding: 12px; border-radius: 10px; border: 1px solid #8886;
          font: inherit; background: transparent; color: inherit; }
  button { padding: 12px 20px; border-radius: 10px; border: 0; background: #2563eb;
           color: #fff; font: inherit; cursor: pointer; }
  button:disabled { opacity: .5; cursor: progress; }
</style>
<h1>وكيل ذكاء اصطناعي على Cloud Run</h1>
<div class="sub">Vertex AI · Gemini · أداة طقس + حاسبة</div>
<div id="log"><div class="msg bot">مرحبًا! اسألني عن الطقس في الجزائر، أو اطلب جمع رقمين.</div></div>
<form id="f">
  <input id="q" placeholder="اكتب رسالتك…" autocomplete="off" required>
  <button id="b">إرسال</button>
</form>
<script>
const log = document.getElementById('log');
const form = document.getElementById('f');
const input = document.getElementById('q');
const btn = document.getElementById('b');
const add = (cls, text) => {
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
};
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  add('user', message);
  input.value = '';
  btn.disabled = true;
  try {
    const r = await fetch('chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await r.json();
    add(r.ok ? 'bot' : 'err', r.ok ? data.reply : ('خطأ: ' + data.error));
  } catch (err) {
    add('err', 'تعذّر الاتصال: ' + err.message);
  } finally {
    btn.disabled = false;
    input.focus();
  }
});
input.focus();
</script>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
