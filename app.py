from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from google import genai
import os
import base64
import zipfile
import warnings

warnings.filterwarnings("ignore")

# Авто-распаковка архивов на сервере Render
for zip_name, folder_name in [("templates.zip", "templates"), ("knowledge_base.zip", "knowledge_base")]:
    if not os.path.exists(folder_name) and os.path.exists(zip_name):
        with zipfile.ZipFile(zip_name, "r") as zip_ref:
            zip_ref.extractall(".")

app = FastAPI()

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

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
3. Respond ONLY to the user's specific statement or question. Do NOT assume specific advanced topics unless mentioned.
"""

def get_knowledge_base():
    try:
        kb_path = "knowledge_base"
        cache_file = os.path.join(kb_path, "_parsed_cache.txt")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()[:2000]
    except Exception:
        pass
    return ""

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/chat")
async def chat_endpoint(data: dict):
    user_message = data.get("message", "")
    history = data.get("history", [])
    level = data.get("level", "High School")
    mode = data.get("mode", "General Theory & Concepts")
    file_data = data.get("file", None)

    contents = []
    for m in history:
        contents.append({"role": m["role"], "parts": [{"text": m["content"]}]})
    
    current_parts = []
    if user_message:
        current_parts.append({"text": user_message})
    
    if file_data and "data:" in file_data:
        try:
            header, encoded = file_data.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            current_parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded
                }
            })
        except Exception:
            pass

    if not current_parts:
        current_parts.append({"text": "Hello!"})

    contents.append({"role": "user", "parts": current_parts})

    full_instruction = BASE_INSTRUCTION + f"\nTarget Level: {level}\nActive Study Mode: {mode}\n"

    chem_keywords = ["reaction", "element", "acid", "base", "formula", "calculate", "mechanism", "solution", "bond", "atom", "nmr", "ph"]
    if any(k in user_message.lower() for k in chem_keywords):
        system_context = get_knowledge_base()
        if system_context:
            full_instruction += f"\nREFERENCE KNOWLEDGE:\n{system_context}"

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=contents,
            config={"system_instruction": full_instruction}
        )
        return JSONResponse({"status": "success", "reply": response.text})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)