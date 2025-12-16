from datetime import datetime, timezone
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text


class SalesOrderHeader(db.Model):
    __tablename__ = 'SalesOrderHeader'
    
    SalesOrderID = Column(Integer, primary_key=True, autoincrement=True)
    OrderDate = Column(String(50), nullable=False)
    DueDate = Column(String(50), nullable=True)
    CustomerName = Column(String(255), nullable=False)
    CustomerAddress = Column(Text, nullable=True)
    InvoiceNumber = Column(String(100), unique=True, nullable=True)
    SubTotal = Column(Float, default=0.0, nullable=False)
    TaxAmount = Column(Float, default=0.0, nullable=False)
    TotalAmount = Column(Float, default=0.0, nullable=False)
    Status = Column(String(50), default='Pending', nullable=False)
    CreatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    UpdatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    DocumentPath = Column(String(500), nullable=True)
    
    items = relationship('SalesOrderDetail', back_populates='header', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'SalesOrderID': self.SalesOrderID,
            'OrderDate': self.OrderDate,
            'DueDate': self.DueDate,
            'CustomerName': self.CustomerName,
            'CustomerAddress': self.CustomerAddress,
            'InvoiceNumber': self.InvoiceNumber,
            'SubTotal': self.SubTotal,
            'TaxAmount': self.TaxAmount,
            'TotalAmount': self.TotalAmount,
            'Status': self.Status,
            'CreatedAt': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'UpdatedAt': self.UpdatedAt.isoformat() if self.UpdatedAt else None,
            'DocumentPath': self.DocumentPath,
            'items': [item.to_dict() for item in self.items]
        }
    
    def __repr__(self):
        return f'<SalesOrderHeader {self.InvoiceNumber or self.SalesOrderID}>'


class SalesOrderDetail(db.Model):
    __tablename__ = 'SalesOrderDetail'
    
    SalesOrderDetailID = Column(Integer, primary_key=True, autoincrement=True)
    SalesOrderID = Column(Integer, ForeignKey('SalesOrderHeader.SalesOrderID'), nullable=False)
    ProductName = Column(String(255), nullable=False)
    ProductDescription = Column(Text, nullable=True)
    Quantity = Column(Integer, default=1, nullable=False)
    UnitPrice = Column(Float, nullable=False)
    LineTotal = Column(Float, nullable=False)
    
    header = relationship('SalesOrderHeader', back_populates='items')
    
    def to_dict(self):
        return {
            'SalesOrderDetailID': self.SalesOrderDetailID,
            'SalesOrderID': self.SalesOrderID,
            'ProductName': self.ProductName,
            'ProductDescription': self.ProductDescription,
            'Quantity': self.Quantity,
            'UnitPrice': self.UnitPrice,
            'LineTotal': self.LineTotal
        }
    
    def __repr__(self):
        return f'<SalesOrderDetail {self.ProductName}>'

