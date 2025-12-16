from flask import Blueprint, send_file, current_app, jsonify
from app.models.sales_order import SalesOrderHeader
from app.services.r2_storage import get_r2_storage
import os
import tempfile

files_bp = Blueprint('files', __name__)


@files_bp.route('/files/<int:sales_order_id>', methods=['GET'])
def download_file(sales_order_id):
    try:
        invoice = SalesOrderHeader.query.get_or_404(sales_order_id)
        
        if not invoice.DocumentPath:
            return jsonify({'error': 'File not found'}), 404
        
        use_r2 = current_app.config.get('USE_R2_STORAGE', False)
        
        if use_r2:
            r2_storage = get_r2_storage()
            file_content = r2_storage.download_file(invoice.DocumentPath)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(file_content)
            temp_file.close()
            
            filename = os.path.basename(invoice.DocumentPath)
            if filename.startswith('invoices/'):
                filename = filename.replace('invoices/', '')
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        else:
            upload_folder = current_app.config['UPLOAD_FOLDER']
            file_path = os.path.join(upload_folder, invoice.DocumentPath)
            
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found'}), 404
            
            return send_file(file_path, as_attachment=True)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/files/<int:sales_order_id>/url', methods=['GET'])
def get_file_url(sales_order_id):
    try:
        invoice = SalesOrderHeader.query.get_or_404(sales_order_id)
        
        if not invoice.DocumentPath:
            return jsonify({'error': 'File not found'}), 404
        
        use_r2 = current_app.config.get('USE_R2_STORAGE', False)
        
        if not use_r2:
            return jsonify({'error': 'Presigned URLs only available with R2 storage'}), 400
        
        r2_storage = get_r2_storage()
        expiration = int(current_app.config.get('R2_PRESIGNED_URL_EXPIRATION', 3600))
        url = r2_storage.get_presigned_url(invoice.DocumentPath, expiration=expiration)
        
        return jsonify({
            'url': url,
            'expiresIn': expiration
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

