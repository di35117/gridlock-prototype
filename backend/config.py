import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL         = os.getenv("DATABASE_URL", "postgresql+asyncpg://btp_user:btp_pass@localhost:5432/btp_intelligence")
REDIS_URL            = os.getenv("REDIS_URL", "redis://localhost:6379")
HUGGINGFACE_API_KEY  = os.getenv("HUGGINGFACE_API_KEY", "")
GOOGLE_MAPS_API_KEY  = os.getenv("GOOGLE_MAPS_API_KEY", "")
SECRET_KEY           = os.getenv("SECRET_KEY", "btp_dev_secret_2026")
BENGALURU_GRAPH_CACHE = os.getenv(
    "BENGALURU_GRAPH_CACHE",
    str(Path(__file__).parent.parent / "data" / "bengaluru_road_graph.graphml")
)

# Resolve DATA_PATH relative to project root
_data_path_env = os.getenv("DATA_PATH", "../data/astram_events.csv")
if not os.path.isabs(_data_path_env):
    DATA_PATH = str((Path(__file__).parent / _data_path_env).resolve())
else:
    DATA_PATH = _data_path_env