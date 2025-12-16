import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.sales_order import SalesOrderHeader, SalesOrderDetail
from app.services.document_extractor import DocumentExtractor
from app.services.r2_storage import get_r2_storage

invoices_bp = Blueprint('invoices', __name__)


@invoices_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200


@invoices_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    extractor = DocumentExtractor()
    
    if not extractor.allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    use_r2 = current_app.config.get('USE_R2_STORAGE', False)
    temp_file_path = None
    
    try:
        filename = secure_filename(file.filename)
        file_type = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        if use_r2:
            try:
                r2_storage = get_r2_storage()
            except ValueError as e:
                current_app.logger.error(f"R2 storage initialization failed: {str(e)}")
                return jsonify({'error': f'R2 storage not configured: {str(e)}'}), 500
            
            content_type_map = {
                'pdf': 'application/pdf',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'txt': 'text/plain'
            }
            content_type = content_type_map.get(file_type, 'application/octet-stream')
            
            object_key = f"invoices/{unique_filename}"
            try:
                r2_url = r2_storage.upload_file(file, object_key, content_type=content_type)
            except Exception as e:
                current_app.logger.error(f"Failed to upload file to R2: {str(e)}")
                return jsonify({'error': f'Failed to upload file to R2: {str(e)}'}), 500
            
            try:
                temp_file_path = r2_storage.download_to_temp_file(object_key)
                file_path = temp_file_path
            except Exception as e:
                current_app.logger.error(f"Failed to download file from R2 for processing: {str(e)}")
                return jsonify({'error': f'Failed to process file: {str(e)}'}), 500
            
            document_path = object_key
        else:
            current_app.logger.warning("Using local file storage - R2 storage is not enabled")
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            document_path = unique_filename
        
        extracted_data = extractor.extract_invoice_data(file_path, file_type)
        
        sales_order_id = _save_invoice_to_db(extracted_data, document_path)
        
        return jsonify({
            'success': True,
            'salesOrderId': sales_order_id,
            'data': extracted_data,
            'documentUrl': r2_url if use_r2 else None
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass


@invoices_bp.route('/invoices', methods=['GET'])
def get_invoices():
    try:
        invoices = SalesOrderHeader.query.order_by(SalesOrderHeader.CreatedAt.desc()).all()
        return jsonify([invoice.to_dict() for invoice in invoices]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/invoices/<int:sales_order_id>', methods=['GET'])
def get_invoice(sales_order_id):
    try:
        invoice = SalesOrderHeader.query.get_or_404(sales_order_id)
        return jsonify(invoice.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/invoices/<int:sales_order_id>', methods=['PUT'])
def update_invoice(sales_order_id):
    try:
        invoice = SalesOrderHeader.query.get_or_404(sales_order_id)
        data = request.json
        
        # Ensure OrderDate is never None
        order_date = data.get('orderDate')
        if order_date:
            invoice.OrderDate = order_date
        elif invoice.OrderDate is None:
            invoice.OrderDate = datetime.now().strftime('%Y-%m-%d')
        invoice.DueDate = data.get('dueDate', invoice.DueDate)
        invoice.CustomerName = data.get('customerName', invoice.CustomerName)
        invoice.CustomerAddress = data.get('customerAddress', invoice.CustomerAddress)
        invoice.InvoiceNumber = data.get('invoiceNumber', invoice.InvoiceNumber)
        invoice.SubTotal = data.get('subTotal', invoice.SubTotal)
        invoice.TaxAmount = data.get('taxAmount', invoice.TaxAmount)
        invoice.TotalAmount = data.get('totalAmount', invoice.TotalAmount)
        invoice.Status = data.get('status', invoice.Status)
        
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/invoices/<int:sales_order_id>/items/<int:item_id>', methods=['PUT'])
def update_invoice_item(sales_order_id, item_id):
    try:
        item = SalesOrderDetail.query.filter_by(
            SalesOrderDetailID=item_id,
            SalesOrderID=sales_order_id
        ).first_or_404()
        
        data = request.json
        
        item.ProductName = data.get('productName', item.ProductName)
        item.ProductDescription = data.get('productDescription', item.ProductDescription)
        item.Quantity = data.get('quantity', item.Quantity)
        item.UnitPrice = data.get('unitPrice', item.UnitPrice)
        item.LineTotal = data.get('lineTotal', item.LineTotal)
        
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/invoices/<int:sales_order_id>', methods=['DELETE'])
def delete_invoice(sales_order_id):
    try:
        invoice = SalesOrderHeader.query.get_or_404(sales_order_id)
        
        use_r2 = current_app.config.get('USE_R2_STORAGE', False)
        if use_r2 and invoice.DocumentPath:
            try:
                r2_storage = get_r2_storage()
                r2_storage.delete_file(invoice.DocumentPath)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete file from R2: {str(e)}")
        elif not use_r2 and invoice.DocumentPath:
            upload_folder = current_app.config['UPLOAD_FOLDER']
            file_path = os.path.join(upload_folder, invoice.DocumentPath)
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except Exception:
                    pass
        
        db.session.delete(invoice)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def _save_invoice_to_db(data: dict, document_path: str) -> int:
    try:
        invoice_number = data.get('invoiceNumber', '').strip()
        
        # Ensure OrderDate has a default value if not provided
        order_date = data.get('orderDate')
        if not order_date:
            order_date = datetime.now().strftime('%Y-%m-%d')
        
        header = None
        if invoice_number:
            header = SalesOrderHeader.query.filter_by(InvoiceNumber=invoice_number).first()
        
        if header:
            header.OrderDate = data.get('orderDate') or header.OrderDate or order_date
            header.DueDate = data.get('dueDate', header.DueDate)
            header.CustomerName = data.get('customerName', header.CustomerName)
            header.CustomerAddress = data.get('customerAddress', header.CustomerAddress)
            header.SubTotal = data.get('subTotal', header.SubTotal)
            header.TaxAmount = data.get('taxAmount', header.TaxAmount)
            header.TotalAmount = data.get('totalAmount', header.TotalAmount)
            header.DocumentPath = document_path
            
            SalesOrderDetail.query.filter_by(SalesOrderID=header.SalesOrderID).delete()
            
            items = data.get('items', [])
            for item_data in items:
                item = SalesOrderDetail(
                    SalesOrderID=header.SalesOrderID,
                    ProductName=item_data.get('productName', ''),
                    ProductDescription=item_data.get('productDescription', ''),
                    Quantity=item_data.get('quantity', 1),
                    UnitPrice=item_data.get('unitPrice', 0),
                    LineTotal=item_data.get('lineTotal', 0)
                )
                db.session.add(item)
        else:
            header = SalesOrderHeader(
                OrderDate=order_date,
                DueDate=data.get('dueDate'),
                CustomerName=data.get('customerName', ''),
                CustomerAddress=data.get('customerAddress', ''),
                InvoiceNumber=invoice_number,
                SubTotal=data.get('subTotal', 0),
                TaxAmount=data.get('taxAmount', 0),
                TotalAmount=data.get('totalAmount', 0),
                Status='Pending',
                DocumentPath=document_path
            )
            
            db.session.add(header)
            db.session.flush()
            
            items = data.get('items', [])
            for item_data in items:
                item = SalesOrderDetail(
                    SalesOrderID=header.SalesOrderID,
                    ProductName=item_data.get('productName', ''),
                    ProductDescription=item_data.get('productDescription', ''),
                    Quantity=item_data.get('quantity', 1),
                    UnitPrice=item_data.get('unitPrice', 0),
                    LineTotal=item_data.get('lineTotal', 0)
                )
                db.session.add(item)
        
        db.session.commit()
        return header.SalesOrderID
    except IntegrityError as e:
        db.session.rollback()
        if 'InvoiceNumber' in str(e.orig):
            invoice_number = data.get('invoiceNumber', '').strip()
            if invoice_number:
                header = SalesOrderHeader.query.filter_by(InvoiceNumber=invoice_number).first()
                if header:
                    # Ensure OrderDate has a value
                    order_date = data.get('orderDate')
                    if not order_date:
                        order_date = datetime.now().strftime('%Y-%m-%d')
                    header.OrderDate = order_date or header.OrderDate or datetime.now().strftime('%Y-%m-%d')
                    header.DueDate = data.get('dueDate', header.DueDate)
                    header.CustomerName = data.get('customerName', header.CustomerName)
                    header.CustomerAddress = data.get('customerAddress', header.CustomerAddress)
                    header.SubTotal = data.get('subTotal', header.SubTotal)
                    header.TaxAmount = data.get('taxAmount', header.TaxAmount)
                    header.TotalAmount = data.get('totalAmount', header.TotalAmount)
                    header.DocumentPath = document_path
                    
                    SalesOrderDetail.query.filter_by(SalesOrderID=header.SalesOrderID).delete()
                    
                    items = data.get('items', [])
                    for item_data in items:
                        item = SalesOrderDetail(
                            SalesOrderID=header.SalesOrderID,
                            ProductName=item_data.get('productName', ''),
                            ProductDescription=item_data.get('productDescription', ''),
                            Quantity=item_data.get('quantity', 1),
                            UnitPrice=item_data.get('unitPrice', 0),
                            LineTotal=item_data.get('lineTotal', 0)
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    return header.SalesOrderID
        raise e
    except Exception as e:
        db.session.rollback()
        raise e

