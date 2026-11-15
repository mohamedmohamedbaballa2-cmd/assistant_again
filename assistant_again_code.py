import re
import time
from io import BytesIO

import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS

st.set_page_config(page_title="مساعدي الذكي", page_icon="🤖")
st.title("🤖 مساعدي الذكي")

MODEL = st.secrets.get("MODEL", "gemini-3.8-flash")
SYSTEM = (
    "أنت مساعد شخصي خبير يساعد في الدراسة والأعمال المكتبية وكتابة أكواد بايثون، "
    "ويرتب المهام ويترجم ويحلل الصور والملفات الصوتية وملفات PDF، "
    "ويساعد في اتخاذ القرارات بذكر الخيارات والمقارنة بينها. "
    "استخدم الأدوات لإدارة المهام. أجب بلغة المستخدم."
)

# ---------- الحالة ----------
st.session_state.setdefault("tasks", [])
st.session_state.setdefault("display", [])
st.session_state.setdefault("mic_n", 0)

# ---------- الأدوات ----------
def add_task(title: str, due: str = "") -> str:
    """يضيف مهمة جديدة إلى قائمة المهام مع موعد اختياري."""
    tasks = st.session_state.tasks
    task = {"id": len(tasks) + 1, "title": title, "due": due, "done": False}
    tasks.append(task)
    return f"تمت إضافة المهمة رقم {task['id']}"

def list_tasks() -> list:
    """يعرض كل المهام الحالية."""
    return st.session_state.tasks

def complete_task(task_id: int) -> str:
    """يحدد مهمة كمنجزة باستخدام رقمها."""
    for t in st.session_state.tasks:
        if t["id"] == task_id:
            t["done"] = True
            return "تم إنجاز المهمة"
    return "المهمة غير موجودة"

# ---------- الاتصال بـ Gemini ----------
if "chat" not in st.session_state:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    st.session_state.chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            tools=[add_task, list_tasks, complete_task],
        ),
    )

def ask(parts):
    """يرسل الطلب مع إعادة المحاولة عند ازدحام الخادم."""
    for i in range(4):
        try:
            return st.session_state.chat.send_message(parts).text, True
        except Exception as e:
            busy = "503" in str(e) or "UNAVAILABLE" in str(e)
            if busy and i < 3:
                time.sleep(2 ** (i + 1))
                continue
            return f"حدث خطأ: {e}", False

# ---------- الصوت ----------
def speak(text):
    """يحول النص إلى صوت (عربي أو إنجليزي حسب اللغة الغالبة)."""
    clean = re.sub(r"[*#`_>|]", " ", text)[:1500]
    arabic = len(re.findall(r"[\u0600-\u06FF]", clean))
    letters = len(re.findall(r"\w", clean)) or 1
    lang = "ar" if arabic / letters > 0.3 else "en"
    try:
        buf = BytesIO()
        gTTS(clean, lang=lang).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None

# ---------- العرض ----------
def render(msg):
    with st.chat_message(msg["role"]):
        for mime, data in msg.get("media", []):
            if mime.startswith("image/"):
                st.image(data)
            elif mime.startswith("audio/"):
                st.audio(data)
            else:
                st.caption("📄 ملف مرفق")
        if msg.get("text"):
            st.write(msg["text"])
        if msg.get("audio"):
            st.audio(msg["audio"], autoplay=bool(msg.get("autoplay")))
            msg["autoplay"] = False

def process(text, files, voice=None):
    parts, media = [], []
    for f in files or []:
        data = f.getvalue()
        parts.append(types.Part.from_bytes(data=data, mime_type=f.type))
        media.append((f.type, data))
    if voice:
        parts.append(types.Part.from_bytes(data=voice, mime_type="audio/wav"))
        media.append(("audio/wav", voice))
        parts.append(
            "هذه رسالة صوتية مني. افهمها وأجب عليها مباشرة بنفس لغة الكلام، "
            "وبإيجاز مناسب للاستماع."
        )
    if text:
        parts.append(text)
    elif files and not voice:
        parts.append("حلّل هذه الملفات وأخبرني بأهم ما فيها.")

    user_msg = {"role": "user", "text": text, "media": media}
    st.session_state.display.append(user_msg)
    render(user_msg)

    with st.chat_message("assistant"):
        with st.spinner("أفكر..."):
            answer, ok = ask(parts)
            audio = speak(answer) if (ok and st.session_state.get("voice_on", True)) else None

    st.session_state.display.append(
        {"role": "assistant", "text": answer, "audio": audio, "autoplay": True}
    )
    st.rerun()

# ---------- الشريط الجانبي ----------
with st.sidebar:
    st.toggle("🔊 رد صوتي", value=True, key="voice_on")
    st.header("📋 مهامي")
    if not st.session_state.tasks:
        st.caption("لا توجد مهام بعد")
    for t in st.session_state.tasks:
        mark = "✅" if t["done"] else "⬜"
        due = f" ({t['due']})" if t["due"] else ""
        st.write(f"{mark} {t['id']}. {t['title']}{due}")

# ---------- الواجهة ----------
mic = st.audio_input("🎙️ سجّل رسالة صوتية", key=f"mic_{st.session_state.mic_n}")

for m in st.session_state.display:
    render(m)

if mic:
    st.session_state.mic_n += 1
    process("", [], voice=mic.getvalue())

prompt = st.chat_input(
    "اكتب طلبك أو أرفق صورة/صوت/PDF...",
    accept_file="multiple",
    file_type=["png", "jpg", "jpeg", "webp", "pdf", "mp3", "wav", "ogg", "flac"],
)
if prompt:
    process(prompt.text or "", prompt.files)