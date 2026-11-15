import json
import anthropic
import streamlit as st

st.set_page_config(page_title="مساعدي الذكي", page_icon="🤖")
st.title("🤖 مساعدي الذكي")

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-5-5"
SYSTEM = (
    "أنت مساعد شخصي خبير يساعد في الدراسة والأعمال المكتبية وكتابة أكواد بايثون، "
    "ويرتب المهام ويترجم ويساعد في اتخاذ القرارات بذكر الخيارات والمقارنة بينها. "
    "استخدم الأدوات لإدارة المهام. أجب بلغة المستخدم."
)

# ---------- الحالة ----------
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []
if "display" not in st.session_state:
    st.session_state.display = []

# ---------- الأدوات ----------
TOOLS = [
    {"name": "add_task",
     "description": "يضيف مهمة جديدة مع موعد اختياري",
     "input_schema": {"type": "object",
                      "properties": {"title": {"type": "string"},
                                     "due": {"type": "string", "description": "الموعد (اختياري)"}},
                      "required": ["title"]}},
    {"name": "list_tasks",
     "description": "يعرض كل المهام",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "complete_task",
     "description": "يحدد مهمة كمنجزة باستخدام رقمها",
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "integer"}},
                      "required": ["task_id"]}},
]

def run_tool(name, args):
    tasks = st.session_state.tasks
    if name == "add_task":
        task = {"id": len(tasks) + 1, "title": args["title"],
                "due": args.get("due", ""), "done": False}
        tasks.append(task)
        return f"تمت إضافة المهمة رقم {task['id']}"
    if name == "list_tasks":
        return tasks or "لا توجد مهام"
    if name == "complete_task":
        for t in tasks:
            if t["id"] == args["task_id"]:
                t["done"] = True
                return "تم إنجاز المهمة"
        return "المهمة غير موجودة"
    return "أداة غير معروفة"

# ---------- حلقة الـ Agent ----------
def chat(user_text):
    msgs = st.session_state.api_messages
    msgs.append({"role": "user", "content": user_text})
    while True:
        r = client.messages.create(
            model=MODEL, max_tokens=1500, system=SYSTEM,
            tools=TOOLS, messages=msgs,
        )
        msgs.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            return "".join(b.text for b in r.content if b.type == "text")
        results = []
        for b in r.content:
            if b.type == "tool_use":
                out = run_tool(b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False)})
        msgs.append({"role": "user", "content": results})

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
                answer = chat(prompt)
            except Exception as e:
                answer = f"حدث خطأ: {e}"
        st.write(answer)
    st.session_state.display.append(("assistant", answer))

with st.sidebar:
    st.header("📋 مهامي")
    if not st.session_state.tasks:
        st.caption("لا توجد مهام بعد")
    for t in st.session_state.tasks:
        mark = "✅" if t["done"] else "⬜"
        due = f" ({t['due']})" if t["due"] else ""
        st.write(f"{mark} {t['id']}. {t['title']}{due}")