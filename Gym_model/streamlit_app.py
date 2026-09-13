# Streamlit Chat UI — شغّلها محليًا في VS Code:
#   pip install streamlit
#   streamlit run streamlit_app.py
#
# ده بيستدعي local_agent.py مباشرة في نفس الـ process — مفيش API تانية محلية،
# الاتصال الوحيد عبر الشبكة هو من جوه local_agent.py لـ Kaggle.

import streamlit as st
import uuid

import local_agent

st.set_page_config(page_title="Pulse Fitness Agent", page_icon="🏋️")
st.title("🏋️ Pulse Fitness — Booking Agent")

with st.sidebar:
    st.header("الإعدادات")
    server_url = st.text_input(
        "Kaggle ngrok URL",
        value=local_agent.KAGGLE_SERVER_URL,
        placeholder="https://xxxx-xx-xx-xxx-xx.ngrok-free.app",
        help="انسخ اللينك اللي طلع في خلية Kaggle بعد ما شغّلت kaggle_generate_server.py",
    )
    if server_url:
        local_agent.set_server_url(server_url)

    if "customer_id" not in st.session_state:
        st.session_state.customer_id = f"customer_{uuid.uuid4().hex[:6]}"

    st.text_input("Customer ID", value=st.session_state.customer_id, disabled=True)

    if st.button("🔄 عميل جديد (يمسح الـ memory تبعه)"):
        st.session_state.customer_id = f"customer_{uuid.uuid4().hex[:6]}"
        st.session_state.messages = []
        st.rerun()

    if st.button("✅ اختبر الاتصال بـ Kaggle"):
        import requests
        try:
            r = requests.get(f"{local_agent.KAGGLE_SERVER_URL}/health", timeout=10)
            st.success("متصل ✓") if r.status_code == 200 else st.error(f"Status: {r.status_code}")
        except Exception as e:
            st.error(f"مش قادر أوصل: {e}")


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("اكتب رسالتك هنا...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("بيفكر..."):
            try:
                reply = local_agent.run_agent(user_input, st.session_state.customer_id)
            except Exception as e:
                reply = f"⚠️ حصل خطأ: {e}"
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
