import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from app import create_app
from app.config import Config
from app.extensions import db


env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

app = create_app(Config)


with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

