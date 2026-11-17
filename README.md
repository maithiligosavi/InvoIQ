# InvoIQ 🧾

**InvoIQ** is a full-stack intelligent invoice management platform that automatically extracts, validates, and organises invoice data from PDF documents. Upload a PDF invoice and InvoIQ parses vendor name, invoice number, amounts, tax breakdowns, line items, and more — no manual data entry required.

---

## ✨ Features

- **Smart PDF Parsing** — Regex-based extractor detects vendor, invoice number, dates, totals, subtotals, GST/tax breakdowns, discounts, shipping charges, and line items from raw PDF text.
- **Vendor Auto-Detection** — Recognises major Indian platforms out of the box: Amazon India, Flipkart, Meesho, Myntra, Blinkit, Swiggy, Zepto, Zomato, Nykaa, Ajio, Tata 1mg, and more.
- **Multi-Tenant Auth** — JWT-based authentication with bcrypt password hashing; every user's invoices are fully isolated.
- **Review & Edit** — Parsed invoice fields are surfaced in an editable UI before saving, with missing-field highlights and validation errors.
- **Invoice CRUD** — Create, read, update, and delete invoices via a RESTful API.
- **Analytics Dashboard** — Visualises monthly spend, vendor breakdown, top vendors, and aggregated metrics using Recharts.
- **Duplicate Detection** — Prevents the same invoice (vendor + invoice number) from being saved twice per user.
- **Status Lifecycle** — `Needs Review` → `Extracted` → `Verified` (set only on explicit user save).

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Axios |
| **Backend** | Python, FastAPI, Uvicorn |
| **Database** | PostgreSQL (via SQLAlchemy + psycopg) |
| **Auth** | JWT (python-jose), bcrypt |
| **PDF Parsing** | pypdf |

---

## 📁 Project Structure

```
InvoIQ-main/
├── backend/
│   ├── main.py          # FastAPI app — all API routes
│   ├── parser.py        # PDF invoice parser (vendor detection, field extraction)
│   ├── auth.py          # JWT auth helpers & middleware
│   ├── models.py        # SQLAlchemy ORM models (User, Invoice)
│   ├── database.py      # DB engine, session, and base config
│   ├── requirements.txt # Python dependencies
│   └── .env             # Environment variables (not committed)
├── src/
│   ├── App.tsx                      # Root React component & routing state
│   ├── types.ts                     # Shared TypeScript types
│   ├── services/
│   │   ├── api.ts                   # Axios client & all API calls
│   │   └── mockData.ts              # Optional mock data for dev
│   └── components/
│       ├── auth/AuthModal.jsx       # Login / Register modal
│       ├── dashboard/Dashboard.tsx  # Analytics & summary view
│       ├── invoices/InvoicesTable.tsx # Invoice list & edit
│       ├── upload/UploadCenter.tsx  # PDF upload & parse flow
│       └── layout/                  # Sidebar & Header
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── start-backend.bat    # Windows convenience script
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18 and **npm** / **pnpm**
- **Python** ≥ 3.11
- **PostgreSQL** running locally (or a hosted instance)

---

### 1. Clone the repo

```bash
git clone https://github.com/your-username/InvoIQ.git
cd InvoIQ
```

---

### 2. Backend Setup

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

#### Configure environment variables

Create `backend/.env`:

```env
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=invoiq

# REQUIRED in production — use a long, random secret (e.g. openssl rand -hex 32)
JWT_SECRET=your-very-secret-key

# Set to "development" for local dev to allow an insecure JWT fallback if
# JWT_SECRET is absent. Remove before deploying to production.
ENVIRONMENT=development
```

#### Start the backend

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

### 3. Frontend Setup

From the project root:

```bash
npm install
npm run dev
```

The React app starts at `http://localhost:5173`.

---

### Windows Convenience

Double-click **`start-backend.bat`** to activate the venv and start Uvicorn in one step.

---

## 🔌 API Reference

All invoice endpoints require `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/register` | Register a new user |
| `POST` | `/api/token` | Login — returns JWT |
| `GET`  | `/api/me` | Get current user profile |
| `POST` | `/api/parse` | Parse a PDF → returns extracted fields (no DB write) |
| `POST` | `/api/invoices` | Save a (possibly edited) invoice to the DB |
| `GET`  | `/api/invoices` | List all invoices for the authenticated user |
| `GET`  | `/api/invoices/{id}` | Get a single invoice by ID or invoice number |
| `PUT` / `PATCH` | `/api/invoices/{id}` | Update an invoice |
| `DELETE` | `/api/invoices/{id}` | Delete an invoice |
| `GET`  | `/api/analytics` | Spending analytics for the authenticated user |
| `POST` | `/api/upload` | *(Legacy)* Parse + save in a single request |

---

## 🏗️ How Invoice Parsing Works

1. **PDF text extraction** — `pypdf` reads all pages and concatenates raw text.
2. **Vendor detection** — Pattern-matched against known Indian e-commerce platforms; falls back to `Sold By / Seller` label; then the first meaningful non-header line.
3. **Field extraction** — A cascade of regex patterns extracts invoice number, dates (invoice & due), totals, subtotals, GST/CGST/SGST/IGST amounts, discounts, shipping, currency, order number, and payment method.
4. **Line item parsing** — Table-like rows are detected and parsed into `{description, quantity, unit_price, line_total}` objects.
5. **Validation** — Missing required fields are recorded in `missing_fields`; amount mismatches go into `validation_errors`. Status is set to `Extracted` or `Needs Review` accordingly.

---

## 🔐 Authentication Flow

```
Register / Login  →  JWT (24 h expiry)  →  Bearer token stored in localStorage
   ↓
Every API request attaches  Authorization: Bearer <token>
   ↓
401 response  →  token cleared  →  Auth modal re-opens
```

Passwords are hashed with **bcrypt**. Tokens are signed with **HS256**.

---

## 🧪 Running Tests

```bash
cd backend

# Parser unit tests
python -m pytest test_parser.py -v

# Auth tests
python -m pytest test_auth.py -v

# Multi-tenancy tests
python -m pytest test_multi_tenancy.py -v
```

---

## 📊 Analytics

The `/api/analytics` endpoint returns:

- `totalSpent` — sum of all verified invoice amounts
- `invoiceCount` — total invoices
- `vendorCount` — unique vendors
- `avgInvoiceValue` — mean invoice value
- `monthlySpend` — spend grouped by `YYYY-MM`
- `topVendors` — top vendors by total spend
- `recentInvoices` — the five most recently added invoices

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(optional)* | Full Postgres connection string (e.g. `postgresql://user:pass@host:5432/dbname`). Automatically preferred over discrete `DB_*` variables. |
| `DB_USER` | `postgres` | PostgreSQL username (used if `DATABASE_URL` is omitted). |
| `DB_PASSWORD` | *(required)* | PostgreSQL password. |
| `DB_HOST` | `localhost` | PostgreSQL host. |
| `DB_PORT` | `5432` | PostgreSQL port. |
| `DB_NAME` | `invoiq` | Database name. |
| `JWT_SECRET` | *(required in production)* | 32+ byte random signing secret (`openssl rand -hex 32`). |
| `ENVIRONMENT` | `production` | Set to `development` for local dev or `production` for strict validation. |
| `FRONTEND_URL` | *(optional)* | URL of your production frontend for CORS (e.g. `https://invoiq.vercel.app`). |
| `ENABLE_DOCS` | `false` | Set to `true` to enable `/docs` and `/redoc` in production. |

### Frontend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api` | Base URL pointing to the FastAPI backend API endpoints. |

---

## 🚢 Production Deployment

### Option 1: Docker Compose (All-in-One)

Deploy PostgreSQL, FastAPI backend, and Nginx frontend in a single command:

```bash
# 1. Clone repository
git clone https://github.com/your-username/InvoIQ.git
cd InvoIQ

# 2. Configure environment
cp .env.example .env
cp backend/.env.example backend/.env

# 3. Build & start containers
docker compose up -d --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

---

### Option 2: Cloud PaaS (Frontend on Vercel + Backend on Render/Railway)

1. **Database:** Create a managed PostgreSQL instance on [Supabase](https://supabase.com) or [Neon](https://neon.tech) and copy your `DATABASE_URL`.
2. **Backend (Render / Railway):**
   - Connect your GitHub repository and set the root directory to `backend`.
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2`
   - Set Environment Variables:
     - `DATABASE_URL`: `postgresql://...`
     - `JWT_SECRET`: `<generated 32-byte secret>`
     - `ENVIRONMENT`: `production`
     - `FRONTEND_URL`: `https://your-frontend.vercel.app`
3. **Frontend (Vercel / Netlify):**
   - Connect the repository root.
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Set Environment Variable:
     - `VITE_API_URL`: `https://your-backend.onrender.com/api`

---

## 📝 License

MIT
