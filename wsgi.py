import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from app import create_app
from app.config import Config

application = create_app(Config)

if __name__ == "__main__":
    application.run()
