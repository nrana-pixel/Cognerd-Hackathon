import os
import re
import sys

# Define the path to the .env file relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Script is now in src/utils/, .env is in src/
ENV_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", ".env"))

def update_env(ngrok_url):
    if not os.path.exists(ENV_PATH):
        print(f"❌ Error: Could not find .env file at: {ENV_PATH}")
        return

    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update OLLAMA_BASE_URL
    if "OLLAMA_BASE_URL=" in content:
        content = re.sub(r"OLLAMA_BASE_URL=.*", f"OLLAMA_BASE_URL={ngrok_url}", content)
    else:
        if not content.endswith('\n'):
            content += '\n'
        content += f"OLLAMA_BASE_URL={ngrok_url}\n"

    # Force provider settings for Ollama
    if "DEFAULT_LLM_PROVIDER=" in content:
        content = re.sub(r"DEFAULT_LLM_PROVIDER=.*", "DEFAULT_LLM_PROVIDER=ollama", content)
    else:
        content += "DEFAULT_LLM_PROVIDER=ollama\n"

    if "LLM_MODEL=" in content:
        content = re.sub(r"LLM_MODEL=.*", "LLM_MODEL=llama3", content)
    else:
        content += "LLM_MODEL=llama3\n"

    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"🚀 Success! Updated .env with URL: {ngrok_url}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Paste your new Ngrok URL: ").strip()
    
    if url:
        update_env(url)

# also to update the .env everytime url gets generated run -> python update_env.py "your url" in the terminal 