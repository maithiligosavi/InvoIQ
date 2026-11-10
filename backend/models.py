from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from datetime import datetime
from database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # --- Core identification ---
    vendor_name = Column(String, index=True, nullable=True)
    invoice_number = Column(String, index=True, nullable=True)
    invoice_date = Column(String, nullable=True)                      # ISO YYYY-MM-DD string

    # --- Amounts ---
    total_amount = Column(Float, nullable=True)
    currency = Column(String, default="INR", nullable=True)           # ISO 4217 code e.g. "INR"
    subtotal = Column(Float, nullable=True)                           # pre-tax / pre-shipping total
    tax_amount = Column(Float, nullable=True)                         # total GST / tax paid
    discount = Column(Float, nullable=True)                           # discount deducted
    shipping_charges = Column(Float, nullable=True)                   # delivery / freight charges

    # --- Tax breakup (CGST / SGST / IGST) stored as JSON string ---
    # e.g. '{"CGST_9": 45.0, "SGST_9": 45.0}'
    tax_breakup = Column(Text, nullable=True)

    # --- Dates ---
    due_date = Column(String, nullable=True)                          # ISO YYYY-MM-DD string

    # --- Reference numbers ---
    order_number = Column(String, nullable=True)                      # PO / reference number

    # --- Payment ---
    payment_status_or_method = Column(String, nullable=True)          # e.g. "Paid", "COD", "UPI"

    # --- Line items stored as JSON string ---
    # e.g. '[{"description": "...", "quantity": 1, "unit_price": 499.0, "line_total": 499.0}]'
    line_items = Column(Text, nullable=True)

    # --- Processing metadata ---
    status = Column(String, default="Processed", nullable=True)       # Processed / Pending / Failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Convenience model aliases for multi-tenancy & clean imports
User = UserModel
Invoice = InvoiceModel

