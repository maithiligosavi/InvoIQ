from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, index=True)
    invoice_number = Column(String, unique=True, index=True)
    invoice_date = Column(String)
    total_amount = Column(Float)
    currency = Column(String, default="₹")
    status = Column(String, default="Processed")  # Processed, Pending, Failed
    created_at = Column(DateTime, default=datetime.utcnow)