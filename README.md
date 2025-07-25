# 🌐 VerbaPilot – AI-Powered Translator & Language Playground

VerbaPilot is a colorful Streamlit app that lets you:

- **Translate** text instantly (Azure Translator Free F0 tier)
- Translate into **multiple languages at once**
- Detect and explain **idioms & slang** via your own JSON dictionaries
- Play a **Language Challenge** and earn XP

---

## 🚀 Quick start

```bash
# 1. Clone repo & enter folder
git clone https://github.com/minaal-rizz/CodeAlpha-VerbaPilot.git
cd CodeAlpha_VerbaPilot

# 2. (Optional) create & activate venv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Azure keys
cp .env.example .env   # edit with your real values

# 5. Run
streamlit run app.py
