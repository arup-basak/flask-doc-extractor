import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') 

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError(
            "DATABASE_URL or POSTGRES_URL environment variable is required. "
            "PostgreSQL database connection must be configured."
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp', 'txt'}
    
    R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID', '')
    R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', '')
    R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', '')
    R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', '')
    R2_PRESIGNED_URL_EXPIRATION = int(os.environ.get('R2_PRESIGNED_URL_EXPIRATION', '3600'))
    
    _explicit_r2_setting = os.environ.get('USE_R2_STORAGE', '').lower()
    if _explicit_r2_setting == 'false':
        USE_R2_STORAGE = False
    elif _explicit_r2_setting == 'true':
        USE_R2_STORAGE = True
    else:
        USE_R2_STORAGE = all([
            R2_ACCOUNT_ID,
            R2_ACCESS_KEY_ID,
            R2_SECRET_ACCESS_KEY,
            R2_BUCKET_NAME
        ])
    
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL') or 'gpt-4o-mini'
    
    @staticmethod
    def init_app(app):
        if not app.config.get('USE_R2_STORAGE', False):
            upload_path = Path(app.config['UPLOAD_FOLDER'])
            upload_path.mkdir(parents=True, exist_ok=True)
        else:
            if not all([
                app.config.get('R2_ACCOUNT_ID'),
                app.config.get('R2_ACCESS_KEY_ID'),
                app.config.get('R2_SECRET_ACCESS_KEY'),
                app.config.get('R2_BUCKET_NAME')
            ]):
                raise ValueError(
                    "R2 storage is enabled but credentials are incomplete. "
                    "Please set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME."
                )

