from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    config_class.init_app(app)
    
    if app.config.get('USE_R2_STORAGE'):
        app.logger.info("✓ R2 Storage enabled - files will be stored in Cloudflare R2")
        app.logger.info(f"  Bucket: {app.config.get('R2_BUCKET_NAME')}")
    else:
        app.logger.warning("⚠ Local storage enabled - files will be stored locally")
        app.logger.warning(f"  Upload folder: {app.config.get('UPLOAD_FOLDER')}")
        if app.config.get('R2_ACCOUNT_ID') or app.config.get('R2_ACCESS_KEY_ID'):
            app.logger.warning("  Note: R2 credentials detected but incomplete. Set all R2_* env vars to enable R2 storage.")
    
    CORS(app)
    
    if hasattr(config_class, 'SQLALCHEMY_ENGINE_OPTIONS'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config_class.SQLALCHEMY_ENGINE_OPTIONS
    
    db.init_app(app)
    
    from app.routes.invoices import invoices_bp
    from app.routes.files import files_bp
    app.register_blueprint(invoices_bp, url_prefix='/api')
    app.register_blueprint(files_bp, url_prefix='/api')
    
    with app.app_context():
        db.create_all()
    
    return app

