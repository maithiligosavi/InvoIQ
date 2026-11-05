from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import database
import models
import parser
import auth

# Initialize FastAPI app
app = FastAPI(title="DocuFlow Backend", version="1.0")

# Enable CORS for your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup (creates 'users' and 'invoices' tables if not present)
models.Base.metadata.create_all(bind=database.engine)


# Pydantic models for authentication
class UserAuthRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "DocuFlow Backend API",
        "docs": "/docs",
        "endpoints": {
            "register": "/api/register",
            "token": "/api/token",
            "invoices": "/api/invoices",
            "analytics": "/api/analytics",
            "upload": "/api/upload"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------------------------------------------------------
# AUTHENTICATION ENDPOINTS
# ---------------------------------------------------------

@app.post("/api/register")
async def register(request: Request, db: Session = Depends(database.get_db)):
    content_type = request.headers.get("content-type", "").lower()
    username = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            pass
        if not username and not password:
            try:
                body = await request.json()
                username = body.get("username")
                password = body.get("password")
            except Exception:
                pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )

    clean_username = str(username).strip()
    clean_password = str(password)

    if len(clean_username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters long"
        )
    if len(clean_password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 4 characters long"
        )

    existing_user = db.query(models.UserModel).filter(models.UserModel.username == clean_username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered"
        )

    hashed_pw = auth.get_password_hash(clean_password)
    new_user = models.UserModel(username=clean_username, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = auth.create_access_token(data={"sub": new_user.username})
    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "username": new_user.username
    }


@app.post("/api/token", response_model=TokenResponse)
@app.post("/api/login", response_model=TokenResponse)
async def login_for_access_token(request: Request, db: Session = Depends(database.get_db)):
    content_type = request.headers.get("content-type", "").lower()
    username = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            pass
        if not username and not password:
            try:
                body = await request.json()
                username = body.get("username")
                password = body.get("password")
            except Exception:
                pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )

    clean_username = str(username).strip()
    clean_password = str(password)

    user = db.query(models.UserModel).filter(models.UserModel.username == clean_username).first()
    if not user or not auth.verify_password(clean_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }


@app.get("/api/me")
def get_current_user_profile(current_user: models.UserModel = Depends(auth.get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


# ---------------------------------------------------------
# PROTECTED INVOICE ENDPOINTS
# ---------------------------------------------------------

# 1. Endpoint to Upload and Parse PDF Invoices
@app.post("/api/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    if not (file.filename and file.filename.lower().endswith(".pdf")):
        raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")
    
    if file.content_type:
        ct = file.content_type.lower()
        if ct not in ["application/pdf", "application/x-pdf", "application/octet-stream", "binary/octet-stream"]:
            raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")

    # Read file bytes
    file_bytes = await file.read()

    if not file_bytes or (not file_bytes.startswith(b"%PDF") and b"%PDF-" not in file_bytes[:1024]):
        raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")

    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        if len(reader.pages) == 0:
            raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")

    # Run through your Python PDF parser (unaltered)
    parsed_data = parser.parse_invoice_pdf(file_bytes)
    if parsed_data.get("status") == "Failed":
        detail_msg = parsed_data.get("error_message") or "File type not supported must be a valid invoice"
        raise HTTPException(status_code=400, detail=detail_msg)
    
    # Generate a unique invoice number if duplicate exists
    existing = db.query(models.InvoiceModel).filter(models.InvoiceModel.invoice_number == parsed_data["invoice_number"]).first()
    if existing:
        import uuid
        parsed_data["invoice_number"] = f"{parsed_data['invoice_number']}-{str(uuid.uuid4())[:4].upper()}"

    # Save to SQLite Database
    db_data = {k: v for k, v in parsed_data.items() if hasattr(models.InvoiceModel, k)}
    db_invoice = models.InvoiceModel(**db_data)
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    amount = float(db_invoice.total_amount or 0.0)
    gst = round(amount * 0.18, 2)
    service_charge = round(amount * 0.82, 2)

    # Return structure matching frontend ExtractedInvoice & raw data
    formatted_invoice = {
        "id": f"INV-{db_invoice.id}",
        "vendor": db_invoice.vendor_name or "Unknown Vendor",
        "vendorName": db_invoice.vendor_name or "Unknown Vendor",
        "invoiceId": db_invoice.invoice_number or f"INV-{db_invoice.id}",
        "invoiceNumber": db_invoice.invoice_number or f"INV-{db_invoice.id}",
        "date": db_invoice.invoice_date or db_invoice.created_at.strftime("%Y-%m-%d"),
        "amount": amount,
        "totalAmount": amount,
        "status": db_invoice.status or "Processed",
        "category": "General",
        "currency": db_invoice.currency or "INR",
        "gst": gst,
        "lineItems": [
            {
                "description": f"{db_invoice.vendor_name or 'Vendor'} Service Charge",
                "quantity": 1,
                "unitPrice": service_charge,
                "total": service_charge,
            },
            {
                "description": "GST (18%)",
                "quantity": 1,
                "unitPrice": gst,
                "total": gst,
            }
        ],
    }
    
    return {
        "message": "Invoice processed successfully",
        "data": formatted_invoice,
        **formatted_invoice
    }


# 2. Endpoint to Get All Invoices for the Dashboard Table
@app.get("/api/invoices")
def get_invoices(
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    invoices = db.query(models.InvoiceModel).all()
    return [
        {
            "id": f"INV-{inv.id}",
            "vendor": inv.vendor_name or "Unknown Vendor",
            "invoiceId": inv.invoice_number or f"INV-{inv.id}",
            "date": inv.invoice_date or inv.created_at.strftime("%Y-%m-%d"),
            "amount": inv.total_amount or 0.0,
            "status": inv.status or "Processed",
            "category": "General",
            "currency": inv.currency or "INR",
            "gst": round((inv.total_amount or 0.0) * 0.18, 2),
            "lineItems": [
                {
                    "description": "Invoice Items & Services",
                    "quantity": 1,
                    "unitPrice": inv.total_amount or 0.0,
                    "total": inv.total_amount or 0.0,
                }
            ],
        }
        for inv in invoices
    ]


# 3. Endpoint to Delete an Invoice
@app.delete("/api/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    clean_id = invoice_id.strip()
    inv = None

    # 1. Try finding by invoice_number
    inv = db.query(models.InvoiceModel).filter(models.InvoiceModel.invoice_number == clean_id).first()

    # 2. Try finding by primary key ID if clean_id is numeric or starts with INV-
    if not inv and clean_id.upper().startswith("INV-"):
        suffix = clean_id[4:]
        if suffix.isdigit():
            inv = db.query(models.InvoiceModel).filter(models.InvoiceModel.id == int(suffix)).first()

    if not inv and clean_id.isdigit():
        inv = db.query(models.InvoiceModel).filter(models.InvoiceModel.id == int(clean_id)).first()

    if not inv:
        raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' not found")

    db.delete(inv)
    db.commit()
    return {"message": "Invoice deleted successfully", "id": invoice_id}


# 4. Endpoint to Get Analytics Metrics and Totals
@app.get("/api/analytics")
def get_analytics(
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    invoices = db.query(models.InvoiceModel).all()
    
    processed = [inv for inv in invoices if inv.status == "Processed"]
    total_spent = sum(inv.total_amount or 0.0 for inv in processed)
    total_count = len(invoices)
    vendors = set(inv.vendor_name for inv in invoices if inv.vendor_name)
    avg_value = round(total_spent / len(processed), 2) if processed else 0.0

    # Group monthly spend
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_spend = [{"month": m, "spend": 0.0} for m in month_names]
    
    # Calculate vendor spend
    vendor_spend_map = {}
    for inv in processed:
        v = inv.vendor_name or "Other"
        vendor_spend_map[v] = vendor_spend_map.get(v, 0.0) + (inv.total_amount or 0.0)
    
    vendor_spend = [
        {"vendor": v, "spend": round(amt, 2)}
        for v, amt in sorted(vendor_spend_map.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "metrics": {
            "totalSpent": round(total_spent, 2),
            "invoicesProcessed": total_count,
            "activeVendors": len(vendors),
            "averageInvoiceValue": avg_value,
        },
        "monthlySpend": monthly_spend,
        "vendorSpend": vendor_spend,
    }
