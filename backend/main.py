from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import database
import models
from models import Invoice, User, InvoiceModel, UserModel
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


def init_db():
    try:
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(invoices);")
        columns = [col[1] for col in cursor.fetchall()]
        if columns and "user_id" not in columns:
            cursor.execute("ALTER TABLE invoices ADD COLUMN user_id INTEGER REFERENCES users(id);")
            cursor.execute("UPDATE invoices SET user_id = 1 WHERE user_id IS NULL;")
            conn.commit()

        cursor.execute("CREATE INDEX IF NOT EXISTS ix_invoices_user_id ON invoices (user_id);")

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='ix_invoices_invoice_number';")
        idx_row = cursor.fetchone()
        if idx_row and idx_row[0] and "UNIQUE" in idx_row[0].upper():
            cursor.execute("DROP INDEX IF EXISTS ix_invoices_invoice_number;")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_invoices_invoice_number ON invoices (invoice_number);")
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database schema initialization warning: {e}")


init_db()


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

# 1a. Parse-only endpoint — extracts fields from PDF but does NOT save to DB
@app.post("/api/parse")
@app.post("/parse")
async def parse_invoice_only(
    file: UploadFile = File(...),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    """Parse a PDF invoice and return extracted fields without saving to the database."""
    if not (file.filename and file.filename.lower().endswith(".pdf")):
        raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")

    if file.content_type:
        ct = file.content_type.lower()
        if ct not in ["application/pdf", "application/x-pdf", "application/octet-stream", "binary/octet-stream"]:
            raise HTTPException(status_code=400, detail="File type not supported must be a valid invoice")

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

    parsed_data = parser.parse_invoice_pdf(file_bytes)
    if parsed_data.get("status") == "Failed":
        detail_msg = parsed_data.get("error_message") or "File type not supported must be a valid invoice"
        raise HTTPException(status_code=400, detail=detail_msg)

    import json as _json

    # Normalise line_items to list of dicts for the response
    raw_line_items = parsed_data.get("line_items")
    if isinstance(raw_line_items, str):
        try:
            raw_line_items = _json.loads(raw_line_items)
        except Exception:
            raw_line_items = []
    if raw_line_items:
        response_line_items = [
            {
                "description": item.get("description") or "Item",
                "quantity": item.get("quantity", 1),
                "unitPrice": item.get("unit_price"),
                "total": item.get("line_total"),
            }
            for item in raw_line_items
        ]
    else:
        response_line_items = []

    amount = parsed_data.get("total_amount")
    tax_amount = parsed_data.get("tax_amount")

    return {
        # None returned as-is so the UI can highlight missing fields
        "vendorName": parsed_data.get("vendor_name"),
        "invoiceNumber": parsed_data.get("invoice_number"),
        "date": parsed_data.get("invoice_date"),
        "dueDate": parsed_data.get("due_date"),
        "totalAmount": amount,
        "subtotal": parsed_data.get("subtotal"),
        "taxAmount": tax_amount,
        "currency": parsed_data.get("currency"),
        "orderNumber": parsed_data.get("order_number"),
        "paymentStatusOrMethod": parsed_data.get("payment_status_or_method"),
        # Legacy gst key — None when tax is genuinely unknown (no fake 18% default)
        "gst": tax_amount,
        "lineItems": response_line_items,
        # Fine-grained status payload for UI highlighting
        "status": parsed_data.get("status"),
        "missingFields": parsed_data.get("missing_fields", []),
        "validationErrors": parsed_data.get("validation_errors", []),
    }


# 1b. Save endpoint — persists a (possibly user-edited) invoice payload to the DB
class SaveInvoiceRequest(BaseModel):
    vendorName: str
    invoiceNumber: str
    date: Optional[str] = None
    dueDate: Optional[str] = None
    totalAmount: float
    subtotal: Optional[float] = None
    taxAmount: Optional[float] = None
    gst: Optional[float] = None
    currency: str = "INR"
    orderNumber: Optional[str] = None
    paymentStatusOrMethod: Optional[str] = None
    lineItems: Optional[list] = None


@app.post("/api/invoices")
@app.post("/invoices")
def save_invoice(
    payload: SaveInvoiceRequest,
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    """Save a (possibly user-edited) invoice to the database."""
    import json as _json

    # Duplicate check strictly scoped to current user
    query = db.query(models.InvoiceModel).filter(
        models.InvoiceModel.vendor_name == payload.vendorName,
        models.InvoiceModel.invoice_number == payload.invoiceNumber,
        models.InvoiceModel.user_id == current_user.id,
    )
    if query.first():
        raise HTTPException(status_code=400, detail="This invoice is already uploaded.")

    tax_val = payload.taxAmount if payload.taxAmount is not None else payload.gst

    line_items_json = _json.dumps(
        [
            {
                "description": item.get("description", "Item"),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unitPrice", 0.0),
                "line_total": item.get("total", 0.0),
            }
            for item in (payload.lineItems or [])
        ]
    )

    db_invoice = models.InvoiceModel(
        user_id=current_user.id,
        vendor_name=payload.vendorName,
        invoice_number=payload.invoiceNumber,
        invoice_date=payload.date or None,
        due_date=payload.dueDate or None,
        total_amount=payload.totalAmount,
        subtotal=payload.subtotal,
        tax_amount=tax_val,
        currency=payload.currency,
        order_number=payload.orderNumber or None,
        payment_status_or_method=payload.paymentStatusOrMethod or None,
        line_items=line_items_json,
        status="Verified",   # User explicitly saved — this constitutes manual confirmation
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    amount = float(db_invoice.total_amount or 0.0)
    return {
        "message": "Invoice saved successfully",
        "id": f"INV-{db_invoice.id}",
        "vendor": db_invoice.vendor_name,
        "vendorName": db_invoice.vendor_name,
        "invoiceId": db_invoice.invoice_number,
        "invoiceNumber": db_invoice.invoice_number,
        "date": db_invoice.invoice_date,
        "amount": amount,
        "totalAmount": amount,
        "currency": db_invoice.currency,
        # Legacy gst key — None when genuinely unknown (no fake 18% default)
        "gst": db_invoice.tax_amount,
        "status": "Verified",
        "category": "General",
        "lineItems": payload.lineItems or [],
    }


# 1c. Legacy upload endpoint — still parses AND saves in one shot (kept for compatibility)
@app.post("/api/upload")
@app.post("/upload")
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

    # 1. Before saving an uploaded invoice, query the SQLite database to check if a record
    # with the same vendor_name AND invoice_number already exists for the user.
    vendor_name = parsed_data.get("vendor_name")
    invoice_number = parsed_data.get("invoice_number")

    query = db.query(models.InvoiceModel).filter(
        models.InvoiceModel.vendor_name == vendor_name,
        models.InvoiceModel.invoice_number == invoice_number,
        models.InvoiceModel.user_id == current_user.id
    )

    existing_invoice = query.first()

    # 2. If it exists, abort the insert and return an HTTP 400 with the exact error message:
    # "This invoice is already uploaded."
    if existing_invoice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invoice is already uploaded."
        )

    # Serialize structured fields (tax_breakup, line_items) to JSON strings for SQLite storage
    import json as _json
    if isinstance(parsed_data.get("tax_breakup"), dict):
        parsed_data["tax_breakup"] = _json.dumps(parsed_data["tax_breakup"])
    if isinstance(parsed_data.get("line_items"), list):
        parsed_data["line_items"] = _json.dumps(parsed_data["line_items"])

    # Save to SQLite Database (only fields that exist on the model)
    db_data = {k: v for k, v in parsed_data.items() if hasattr(models.InvoiceModel, k)}
    db_data["user_id"] = current_user.id
    # Persist the parser status — "Verified" can only be set by user action in the UI
    parsed_status = parsed_data.get("status", "Needs Review")
    db_data["status"] = parsed_status if parsed_status in ("Extracted", "Needs Review") else "Needs Review"
    db_invoice = models.InvoiceModel(**db_data)
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    # Deserialize JSON strings back to Python objects for the response
    def _load_json(raw):
        if raw is None:
            return None
        try:
            return _json.loads(raw)
        except (ValueError, TypeError):
            return None

    amount = float(db_invoice.total_amount or 0.0)
    tax_amount = db_invoice.tax_amount
    subtotal = db_invoice.subtotal
    tax_breakup = _load_json(db_invoice.tax_breakup)
    line_items_parsed = _load_json(db_invoice.line_items)

    # Build line_items for the response: use real extracted items if available.
    if line_items_parsed:
        response_line_items = [
            {
                "description": item.get("description") or "Item",
                "quantity": item.get("quantity", 1),
                "unitPrice": item.get("unit_price"),
                "total": item.get("line_total"),
            }
            for item in line_items_parsed
        ]
    else:
        response_line_items = []

    # Return structure matching frontend ExtractedInvoice & raw data
    parsed_status = parsed_data.get("status", "Needs Review")
    # Map parser status to db-persisted status; "Verified" is set by user action only
    db_status = parsed_status if parsed_status in ("Extracted", "Needs Review") else "Needs Review"

    formatted_invoice = {
        "id": f"INV-{db_invoice.id}",
        "vendor": db_invoice.vendor_name,
        "vendorName": db_invoice.vendor_name,
        "invoiceId": db_invoice.invoice_number,
        "invoiceNumber": db_invoice.invoice_number,
        "date": db_invoice.invoice_date,
        "dueDate": db_invoice.due_date,
        "amount": amount,
        "totalAmount": amount,
        "subtotal": subtotal,
        "taxAmount": tax_amount,
        "taxBreakup": tax_breakup,
        "discount": db_invoice.discount,
        "shippingCharges": db_invoice.shipping_charges,
        "currency": db_invoice.currency,
        "orderNumber": db_invoice.order_number,
        "paymentStatusOrMethod": db_invoice.payment_status_or_method,
        "status": db_status,
        "category": "General",
        # Legacy "gst" key — None when tax genuinely unknown (no fake 18% default)
        "gst": tax_amount,
        "lineItems": response_line_items,
        # Fine-grained validation payload for UI highlighting
        "missingFields": parsed_data.get("missing_fields", []),
        "validationErrors": parsed_data.get("validation_errors", []),
    }

    return {
        "message": "Invoice processed successfully",
        "data": formatted_invoice,
        **formatted_invoice
    }


# Helper to format InvoiceModel to dictionary response
def format_invoice_response(inv: models.InvoiceModel) -> dict:
    import json as _json

    def _load_json(raw):
        if raw is None:
            return None
        try:
            return _json.loads(raw)
        except (ValueError, TypeError):
            return None

    amount = float(inv.total_amount or 0.0)
    tax_amount = inv.tax_amount
    line_items_parsed = _load_json(inv.line_items)
    tax_breakup = _load_json(inv.tax_breakup)

    if line_items_parsed:
        response_line_items = [
            {
                "description": item.get("description") or "Item",
                "quantity": item.get("quantity", 1),
                "unitPrice": item.get("unit_price"),
                "total": item.get("line_total"),
            }
            for item in line_items_parsed
        ]
    else:
        response_line_items = []

    return {
        "id": f"INV-{inv.id}",
        "vendor": inv.vendor_name,
        "vendorName": inv.vendor_name,
        "invoiceId": inv.invoice_number,
        "invoiceNumber": inv.invoice_number,
        "date": inv.invoice_date,
        "dueDate": inv.due_date,
        "amount": amount,
        "totalAmount": amount,
        "subtotal": inv.subtotal,
        "taxAmount": tax_amount,
        "taxBreakup": tax_breakup,
        "discount": inv.discount,
        "shippingCharges": inv.shipping_charges,
        "currency": inv.currency,
        "orderNumber": inv.order_number,
        "paymentStatusOrMethod": inv.payment_status_or_method,
        "status": inv.status or "Needs Review",
        "category": "General",
        "gst": tax_amount,
        "lineItems": response_line_items,
    }


def find_invoice_by_id_or_number(db: Session, invoice_id: str, user_id: int) -> Optional[models.InvoiceModel]:
    clean_id = str(invoice_id).strip()
    inv = None

    # 1. Try finding by primary key ID if clean_id is numeric or starts with INV-
    if clean_id.upper().startswith("INV-"):
        suffix = clean_id[4:]
        if suffix.isdigit():
            inv = db.query(models.InvoiceModel).filter(models.InvoiceModel.id == int(suffix)).first()

    if not inv and clean_id.isdigit():
        inv = db.query(models.InvoiceModel).filter(models.InvoiceModel.id == int(clean_id)).first()

    # 2. Try finding by invoice_number for this user first
    if not inv:
        inv = db.query(models.InvoiceModel).filter(
            models.InvoiceModel.invoice_number == clean_id,
            models.InvoiceModel.user_id == user_id
        ).first()

    # 3. If still not found, check across all users by invoice_number (to identify cross-tenant access)
    if not inv:
        inv = db.query(models.InvoiceModel).filter(
            models.InvoiceModel.invoice_number == clean_id
        ).first()

    return inv


# Pydantic model for updating an invoice
class UpdateInvoiceRequest(BaseModel):
    vendorName: Optional[str] = None
    vendor: Optional[str] = None
    invoiceNumber: Optional[str] = None
    invoiceId: Optional[str] = None
    date: Optional[str] = None
    dueDate: Optional[str] = None
    totalAmount: Optional[float] = None
    amount: Optional[float] = None
    subtotal: Optional[float] = None
    taxAmount: Optional[float] = None
    gst: Optional[float] = None
    currency: Optional[str] = None
    orderNumber: Optional[str] = None
    paymentStatusOrMethod: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    lineItems: Optional[list] = None


# 2. Endpoint to Get All Invoices for the Dashboard Table (Scoped Querying)
@app.get("/api/invoices")
@app.get("/invoices")
def get_invoices(
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()
    return [format_invoice_response(inv) for inv in invoices]


# 3a. Endpoint to Get a Single Invoice by ID
@app.get("/api/invoices/{invoice_id}")
@app.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    inv = find_invoice_by_id_or_number(db, invoice_id, current_user.id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found"
        )
    if inv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to access this invoice."
        )
    return format_invoice_response(inv)


# 3b. Endpoint to Edit / Update an Invoice
@app.put("/api/invoices/{invoice_id}")
@app.put("/invoices/{invoice_id}")
@app.patch("/api/invoices/{invoice_id}")
@app.patch("/invoices/{invoice_id}")
def update_invoice(
    invoice_id: str,
    payload: UpdateInvoiceRequest,
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    inv = find_invoice_by_id_or_number(db, invoice_id, current_user.id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found"
        )
    if inv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to edit this invoice."
        )

    if payload.vendorName is not None or payload.vendor is not None:
        inv.vendor_name = payload.vendorName if payload.vendorName is not None else payload.vendor
    if payload.invoiceNumber is not None or payload.invoiceId is not None:
        inv.invoice_number = payload.invoiceNumber if payload.invoiceNumber is not None else payload.invoiceId
    if payload.date is not None:
        inv.invoice_date = payload.date
    if payload.dueDate is not None:
        inv.due_date = payload.dueDate
    if payload.totalAmount is not None or payload.amount is not None:
        inv.total_amount = payload.totalAmount if payload.totalAmount is not None else payload.amount
    if payload.subtotal is not None:
        inv.subtotal = payload.subtotal
    tax = payload.taxAmount if payload.taxAmount is not None else payload.gst
    if tax is not None:
        inv.tax_amount = tax
    if payload.currency is not None:
        inv.currency = payload.currency
    if payload.orderNumber is not None:
        inv.order_number = payload.orderNumber
    if payload.paymentStatusOrMethod is not None:
        inv.payment_status_or_method = payload.paymentStatusOrMethod
    if payload.status is not None:
        inv.status = payload.status

    if payload.lineItems is not None:
        import json as _json
        inv.line_items = _json.dumps(payload.lineItems)

    db.commit()
    db.refresh(inv)

    formatted = format_invoice_response(inv)
    return {
        "message": "Invoice updated successfully",
        **formatted
    }


# 3c. Endpoint to Delete an Invoice
@app.delete("/api/invoices/{invoice_id}")
@app.delete("/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    inv = find_invoice_by_id_or_number(db, invoice_id, current_user.id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found"
        )

    if inv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to delete this invoice."
        )

    db.delete(inv)
    db.commit()
    return {"message": "Invoice deleted successfully", "id": invoice_id}


# 4. Endpoint to Get Analytics Metrics and Totals (Scoped to Authenticated User)
@app.get("/api/analytics")
@app.get("/analytics")
def get_analytics(
    db: Session = Depends(database.get_db),
    current_user: models.UserModel = Depends(auth.get_current_user)
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()
    
    # Include all non-failed/non-pending invoices
    processed = [
        inv for inv in invoices
        if (inv.status or "").lower() not in ("failed", "pending")
    ]
    total_spent = sum(inv.total_amount or 0.0 for inv in processed)
    total_count = len(invoices)
    vendors = set(inv.vendor_name for inv in processed if inv.vendor_name)
    avg_value = round(total_spent / len(processed), 2) if processed else 0.0

    # Group monthly spend
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_spend_map = {m: 0.0 for m in month_names}
    for inv in processed:
        if inv.invoice_date:
            try:
                date_str = str(inv.invoice_date).strip()
                parts = date_str.split("-") if "-" in date_str else date_str.split("/")
                if len(parts) >= 2:
                    if len(parts[0]) == 4 and parts[1].isdigit():
                        m_idx = int(parts[1]) - 1
                    elif len(parts) == 3 and len(parts[2]) == 4 and parts[1].isdigit():
                        m_idx = int(parts[1]) - 1
                    else:
                        m_idx = -1
                    if 0 <= m_idx < 12:
                        monthly_spend_map[month_names[m_idx]] += float(inv.total_amount or 0.0)
            except Exception:
                pass

    monthly_spend = [
        {"month": m, "spend": round(monthly_spend_map[m], 2)}
        for m in month_names
    ]
    
    # Calculate vendor spend
    vendor_spend_map = {}
    for inv in processed:
        v = (inv.vendor_name or "Other").strip()
        vendor_spend_map[v] = vendor_spend_map.get(v, 0.0) + float(inv.total_amount or 0.0)
    
    vendor_spend = [
        {"vendor": v, "spend": round(amt, 2)}
        for v, amt in sorted(vendor_spend_map.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "metrics": {
            "totalSpent": round(total_spent, 2),
            "invoicesProcessed": len(processed),
            "activeVendors": len(vendors),
            "averageInvoiceValue": avg_value,
        },
        "monthlySpend": monthly_spend,
        "vendorSpend": vendor_spend,
    }
