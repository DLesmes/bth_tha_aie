import os
from dotenv import load_dotenv

# Trace upward to locate the root .env workspace file cleanly
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))

class Settings:
    def __init__(self):
        self.app_name = os.getenv('APP_NAME', 'Secure Agentic RAG Endpoint Cluster')
        self.app_version = os.getenv('APP_VERSION', '1.0.0')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Server settings
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = int(os.getenv('PORT', '8000'))

        # Google Generative AI (LLM) Settings
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gemini-flash-lite-latest")

        # Weaviate Settings
        self.WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8050")
        self.WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

        # OpenFGA / Auth0 FGA Settings
        self.FGA_STORE_ID = os.getenv("FGA_STORE_ID")
        self.FGA_CLIENT_ID = os.getenv("FGA_CLIENT_ID")
        self.FGA_CLIENT_SECRET = os.getenv("FGA_CLIENT_SECRET")
        self.FGA_API_AUDIENCE = os.getenv("FGA_API_AUDIENCE")
        self.FGA_API_ISSUER = os.getenv("FGA_API_ISSUER")
        self.FGA_API_TOKEN = os.getenv("FGA_API_TOKEN")
        self.FGA_API_URL = os.getenv("FGA_API_URL", "http://localhost:8081")

        # Identity UI & Pipeline Connectors
        self.DEFAULT_DEMO_ROLE = os.getenv("DEFAULT_DEMO_ROLE", "collaborator")
        self.BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/chat")

# Instantiate singleton for centralized use
settings = Settings()
