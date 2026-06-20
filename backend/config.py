import os
from pathlib import Path
from dotenv import load_dotenv

# config.py and .env are now BOTH in the backend/ folder
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

DATABASE_URL         = os.getenv("DATABASE_URL", "postgresql+asyncpg://btp_user:btp_pass@localhost:5432/btp_intelligence")
REDIS_URL            = os.getenv("REDIS_URL", "redis://localhost:6379")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "")
GOOGLE_MAPS_API_KEY  = os.getenv("GOOGLE_MAPS_API_KEY", "")
SECRET_KEY           = os.getenv("SECRET_KEY", "btp_dev_secret_2026")

# The data folder is one level UP from the backend folder
ROOT_DIR = BASE_DIR.parent

BENGALURU_GRAPH_CACHE = os.getenv(
    "BENGALURU_GRAPH_CACHE",
    str(ROOT_DIR / "data" / "bengaluru_road_graph.graphml")
)

_data_path_env = os.getenv("DATA_PATH", "../data/astram_events.csv")
if not os.path.isabs(_data_path_env):
    DATA_PATH = str((BASE_DIR / _data_path_env).resolve())
else:
    DATA_PATH = _data_path_env