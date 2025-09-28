AI_GM_Project — Security Fix (No manual code editing)

WHAT THIS DOES
1) Creates a .env file and saves your OpenAI API key there.
2) Updates your Python files (chat_api.py and chat_with_wojtek.py) to load the key from .env.
3) Makes safe backups of changed files as .bak.

HOW TO USE (Windows, simplest)
1) Unzip this folder directly into your AI-GM-Project directory.
   - You should end up with: AI-GM-Project\tools\fix_security.py and the .bat files in the project root.
2) Double-click: Run_Fix_Security.bat
   - When asked, paste your OpenAI API key (it starts with sk-...).
   - The script will create or update .env and patch your files safely.
3) (Optional) Double-click: Install_Requirements.bat to install needed packages.

That’s it. No manual code editing required.
