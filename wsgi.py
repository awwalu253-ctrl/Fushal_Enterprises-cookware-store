from app import create_app
import os
import sys

app = create_app()

# For Vercel serverless
handler = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()
handler = app