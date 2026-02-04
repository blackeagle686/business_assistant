import nest_asyncio
import threading
import uvicorn
from pyngrok import ngrok, conf
from app.main import app

# asyncio loop for notebook environments
nest_asyncio.apply()

# start FastAPI in background thread
def run_app():
    uvicorn.run(app, host="0.0.0.0", port=8000)

thread = threading.Thread(target=run_app, daemon=True)
thread.start()

# setup ngrok
# Note: Token is provided by the user in the request
NGROK_TOKEN = "36jW6kAV8Inp5SHYiuIicuuRols_7NkiWdLme3iULLJx3gMS5"
conf.get_default().auth_token = NGROK_TOKEN
public_url = ngrok.connect(8000).public_url
print(f"\n🚀 Public URL: {public_url}\n")
