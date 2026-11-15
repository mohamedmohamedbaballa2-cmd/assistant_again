import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="مساعدي الذكي", page_icon="🤖")
st.title("🤖 مساعدي الذكي")

MODEL = "gemini-3.8-flash"
SYSTEM = (
    "أنت مساعد شخصي خبير يساعد في الدراسة والأعمال المكتبية وكتابة أكواد بايثون، "
    "ويرتب المهام ويترجم ويساعد في اتخاذ القرارات بذكر الخيارات والمقارنة بينها. "
    "استخدم الأدوات لإدارة المهام. أجب بلغة المستخدم."
)

# ---------- الحالة ----------
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "display" not in st.session_state:
    st.session_state.display = []

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

# ---------- الواجهة ----------
for role, text in st.session_state.display:
    with st.chat_message(role):
        st.write(text)

if prompt := st.chat_input("اكتب طلبك هنا..."):
    st.session_state.display.append(("user", prompt))
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("أفكر..."):
            try:
                answer = st.session_state.chat.send_message(prompt).text
            except Exception as e:
                answer = f"حدث خطأ: {e}"
        st.write(answer)
    st.session_state.display.append(("assistant", answer))
    st.rerun()

with st.sidebar:
    st.header("📋 مهامي")
    if not st.session_state.tasks:
        st.caption("لا توجد مهام بعد")
    for t in st.session_state.tasks:
        mark = "✅" if t["done"] else "⬜"
        due = f" ({t['due']})" if t["due"] else ""
        st.write(f"{mark} {t['id']}. {t['title']}{due}")