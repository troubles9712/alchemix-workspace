import streamlit as st
from google import genai
import os
import warnings
from pypdf import PdfReader

# Игнорируем предупреждения PDF-парсера
warnings.filterwarnings("ignore")

# 1. Page Config
st.set_page_config(
    page_title="Alchemix | AI Chemistry Workspace",
    page_icon="⚗️",
    layout="wide"
)

# 2. Premium Neon Glassmorphism CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@600;700;800&display=swap');

    /* Фон с яркими неоновыми свечениями */
    .stApp {
        background: radial-gradient(circle at 12% 12%, rgba(16, 185, 129, 0.16) 0%, transparent 45%),
                    radial-gradient(circle at 88% 88%, rgba(99, 102, 241, 0.15) 0%, transparent 45%),
                    #060911 !important;
        color: #F8FAFC !important;
    }

    /* Боковая панель */
    section[data-testid="stSidebar"] {
        background: rgba(13, 20, 36, 0.85) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(52, 211, 153, 0.25) !important;
    }

    /* Главный Баннер-Карточка */
    .hero-card {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(99, 102, 241, 0.18) 100%);
        border: 1px solid rgba(52, 211, 153, 0.45);
        border-radius: 20px;
        padding: 26px 30px;
        margin-bottom: 24px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.4), 0 0 20px rgba(16, 185, 129, 0.15);
        backdrop-filter: blur(12px);
    }
    .hero-title {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #34D399 0%, #10B981 50%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
        letter-spacing: -0.02em;
    }

    /* Бейджи параметров */
    .badge-container {
        display: flex;
        gap: 12px;
        margin-top: 14px;
    }
    .badge-emerald {
        background: rgba(16, 185, 129, 0.25);
        color: #34D399;
        border: 1px solid rgba(52, 211, 153, 0.5);
        padding: 6px 16px;
        border-radius: 30px;
        font-size: 0.85rem;
        font-weight: 700;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
    }
    .badge-indigo {
        background: rgba(99, 102, 241, 0.25);
        color: #A5B4FC;
        border: 1px solid rgba(129, 140, 248, 0.5);
        padding: 6px 16px;
        border-radius: 30px;
        font-size: 0.85rem;
        font-weight: 700;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.25);
    }

    /* Сообщения в чате */
    .stChatMessage {
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(52, 211, 153, 0.22) !important;
        border-radius: 18px !important;
        padding: 18px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(10px) !important;
    }

    /* Кнопки с неоновой подсветкой */
    .stButton>button {
        border-radius: 14px !important;
        border: 1px solid rgba(52, 211, 153, 0.4) !important;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.18) 0%, rgba(30, 41, 59, 0.9) 100%) !important;
        color: #F8FAFC !important;
        font-weight: 700 !important;
        transition: all 0.25s ease !important;
    }
    .stButton>button:hover {
        border-color: #34D399 !important;
        color: #34D399 !important;
        box-shadow: 0 0 22px rgba(16, 185, 129, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    /* Поле ввода вопроса */
    div[data-testid="stChatInput"] {
        border-radius: 20px !important;
        border: 1.5px solid rgba(52, 211, 153, 0.4) !important;
        background: rgba(15, 23, 42, 0.95) !important;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.15) !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #34D399 !important;
        box-shadow: 0 0 30px rgba(52, 211, 153, 0.4) !important;
    }

    /* Точечный перекрас ползунка Slider в неоново-зеленый */
    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background-color: #34D399 !important;
        box-shadow: 0 0 14px #34D399 !important;
        border: 2px solid #060911 !important;
    }
    .stSlider [data-baseweb="slider"] div {
        background: linear-gradient(90deg, #10B981 0%, #34D399 100%) !important;
    }
    .stSlider [data-testid="stWidgetLabel"] p {
        color: #34D399 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# Быстрая загрузка базы знаний с кэшированием
@st.cache_data
def load_system_knowledge():
    kb_path = "knowledge_base"
    cache_file = os.path.join(kb_path, "_parsed_cache.txt")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()[:3000]
        except Exception:
            pass

    combined_text = ""
    if os.path.exists(kb_path):
        for file in os.listdir(kb_path):
            if file.startswith("_"):
                continue
            file_path = os.path.join(kb_path, file)
            
            if file.endswith(".pdf"):
                try:
                    reader = PdfReader(file_path)
                    for i in range(min(8, len(reader.pages))):
                        text = reader.pages[i].extract_text()
                        if text:
                            combined_text += text + "\n"
                except Exception:
                    pass
            elif file.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        combined_text += f.read() + "\n"
                except Exception:
                    pass

        if combined_text:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(combined_text)
            except Exception:
                pass

    return combined_text[:3000]

# Инициализация Gemini
@st.cache_resource
def get_client():
   return genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

client = get_client()

BASE_INSTRUCTION = r"""You are Alchemix, an expert, enthusiastic, and highly structured AI Chemistry Tutor.

ADAPTATION BY STUDY MODE:
- 'General Theory & Concepts': Focus on high-level intuitive understanding, real-world analogies, and fundamental laws.
- 'Step-by-Step Problem Solving': Structure response explicitly into 'Given', 'Relevant Formulas', 'Execution & Math', and 'Final Answer with Units'.
- 'Reaction Mechanisms & Curved Arrows': Break down electron movements, nucleophile/electrophile interactions, and intermediates.
- 'Reaction Balancing & Redox': Provide oxidation states breakdown, half-reactions, and balanced equations.
- 'Exam Prep & Practice Quiz': Act as an exam mentor. Give hints first, present test-style questions, and critique reasoning.
- 'Lab Assistant & Safety': Focus on experimental procedure, qualitative changes, apparatus setup, and safety.

RULES:
1. Tailor depth precisely to the user's selected Target Difficulty Level.
2. Always use LaTeX formatting for formulas and equations (e.g., $H_2SO_4$, $\Delta H$).
3. Greet ONLY on the very first message or if user greets you. Never repeat greetings on follow-up questions.
"""

# Инициализация диалога
if "chats" not in st.session_state:
    st.session_state.chats = {"New Session": []}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "New Session"

system_context = load_system_knowledge()

# Боковая панель
with st.sidebar:
    st.markdown("<h2 style='font-family: \"Space Grotesk\", sans-serif; color:#34D399; margin-bottom:0;'>⚗️ Alchemix</h2>", unsafe_allow_html=True)
    st.caption("AI Chemistry Workspace & Tutor")
    
    if system_context:
        st.success("📚 Knowledge Base Active")
    
    st.markdown("---")
    
    if st.button("✨ New Session", use_container_width=True):
        count = len(st.session_state.chats) + 1
        new_chat_name = f"Chat {count}"
        st.session_state.chats[new_chat_name] = []
        st.session_state.active_chat = new_chat_name
        st.rerun()

    st.markdown("#### 💬 Recents")
    for chat_name in list(st.session_state.chats.keys()):
        is_active = chat_name == st.session_state.active_chat
        icon = "🧪" if is_active else "📄"
        if st.button(f"{icon} {chat_name}", key=f"btn_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()

    st.markdown("---")
    st.markdown("#### ⚙️ Settings & Level")
    
    level = st.select_slider(
        "Target Level:",
        options=["Middle School", "High School", "AP/IB / AS-Level", "College / Olympiad"]
    )
    
    mode = st.selectbox(
        "Study Mode:",
        [
            "General Theory & Concepts",
            "Step-by-Step Problem Solving",
            "Reaction Mechanisms & Curved Arrows",
            "Reaction Balancing & Redox",
            "Exam Prep & Practice Quiz",
            "Lab Assistant & Safety"
        ]
    )
    
    user_file = st.file_uploader(
        "Attach Homework / Problem Sheet:",
        type=["pdf", "txt", "png", "jpg"]
    )

# Главная карточка-баннер
st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">⚗️ Alchemix</div>
    <div style="color: #94A3B8; font-size: 1.05rem; font-weight: 500;">
        Interactive AI Chemistry Workspace & Academic Problem Solver
    </div>
    <div class="badge-container">
        <span class="badge-emerald">🎯 Level: {level}</span>
        <span class="badge-indigo">⚙️ Mode: {mode}</span>
    </div>
</div>
""", unsafe_allow_html=True)

current_messages = st.session_state.chats[st.session_state.active_chat]

# Отображение диалога
for msg in current_messages:
    icon = "🧑‍🎓" if msg["role"] == "user" else "⚗️"
    st.chat_message(msg["role"], avatar=icon).write(msg["content"])

# Ввод пользователя
if user_input := st.chat_input("Ask a chemistry question, equation, or topic..."):
    current_messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="🧑‍🎓").write(user_input)

    if len(current_messages) == 1:
        new_title = user_input[:18] + "..." if len(user_input) > 18 else user_input
        st.session_state.chats[new_title] = st.session_state.chats.pop(st.session_state.active_chat)
        st.session_state.active_chat = new_title

    contents = []
    for m in current_messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    prompt_config = {
        "system_instruction": BASE_INSTRUCTION + f"\nTarget Level: {level}\nStudy Mode: {mode}\n"
    }
    
    if system_context and len(user_input.split()) > 2:
        prompt_config["system_instruction"] += f"\nTEXTBOOK KNOWLEDGE:\n{system_context}"

    with st.chat_message("assistant", avatar="⚗️"):
        with st.spinner("Transmuting knowledge..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=contents,
                    config=prompt_config
                )
                st.markdown(response.text)
                current_messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Error generating response: {e}")