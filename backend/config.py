import os
from pathlib import Path
from dotenv import load_dotenv

# BASE_DIR is the backend/ folder
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

DATABASE_URL          = os.getenv("DATABASE_URL", "postgresql+asyncpg://btp_user:btp_pass@localhost:5432/btp_intelligence")
REDIS_URL             = os.getenv("REDIS_URL", "redis://localhost:6379")
GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY", "")
GOOGLE_MAPS_API_KEY   = os.getenv("GOOGLE_MAPS_API_KEY", "")
SECRET_KEY            = os.getenv("SECRET_KEY", "btp_dev_secret_2026")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# --- MapmyIndia Enterprise Credentials ---
MAPMYINDIA_STATIC_KEY    = os.getenv("MAPMYINDIA_STATIC_KEY", "")
MAPMYINDIA_CLIENT_ID     = os.getenv("MAPMYINDIA_CLIENT_ID", "")
MAPMYINDIA_CLIENT_SECRET = os.getenv("MAPMYINDIA_CLIENT_SECRET", "")

# We safely construct absolute paths so Docker/Railway can always find them.
DATA_PATH = os.getenv(
    "DATA_PATH", 
    str(BASE_DIR / "data" / "astram_events.csv")
)