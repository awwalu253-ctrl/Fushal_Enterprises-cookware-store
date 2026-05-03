from app import create_app
import os

app = create_app()

# For Vercel serverless
def handler(request, context):
    """Vercel serverless function handler"""
    return app(request.environ, lambda status, headers, exc_info=None: None)

# For local development
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)