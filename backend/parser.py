import io
import json
import re
from datetime import datetime
from pypdf import PdfReader


# ============================================================
# VENDOR DETECTION
# ============================================================

def extract_vendor_name(text: str) -> str:
    """
    Dynamically recognize vendors from extracted invoice text.
    Detects major e-commerce platforms like Amazon India, Flipkart, and Meesho,
    plus common quick-commerce/retail services and labeled seller lines.
    """
    text_lower = text.lower()

    # 1. Platform-specific keyword detection
    if re.search(r"\bamazon\b|amazon\s*(?:india|\.in|seller|retail|wholesale)|cloudtail|appario|prione", text_lower):
        return "Amazon India"

    if re.search(r"\bflipkart\b|flipkart\s*(?:internet|india)|ws\s*retail", text_lower):
        return "Flipkart"

    if re.search(r"\bmeesho\b|fashnear", text_lower):
        return "Meesho"

    if re.search(r"\bmyntra\b", text_lower):
        return "Myntra"

    if re.search(r"\bblinkit\b|\bgrofers\b", text_lower):
        return "Blinkit"

    if re.search(r"\bswiggy\b|instamart", text_lower):
        return "Swiggy"

    if re.search(r"\bzepto\b", text_lower):
        return "Zepto"

    if re.search(r"\bzomato\b", text_lower):
        return "Zomato"

    if re.search(r"\bnykaa\b", text_lower):
        return "Nykaa"

    if re.search(r"\bajio\b", text_lower):
        return "Ajio"

    if re.search(r"\btata\s*1mg\b|1mg\s*technologies", text_lower):
        return "Tata 1mg"

    # 2. Check for explicit "Sold By / Seller / Billed By" labels
    seller_match = re.search(
        r"(?:Sold\s+By|Seller|Billed\s+By|Vendor\s*Name|Supplier)\s*[:\-]\s*([^\r\n,;]+)",
        text,
        re.IGNORECASE,
    )
    if seller_match:
        name = seller_match.group(1).strip()
        if len(name) >= 2:
            return name[:40].strip()

    # 3. Fallback: First meaningful line that is not a generic invoice header
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skip_headers = {
        "tax invoice", "invoice", "bill of supply", "retail invoice",
        "original for recipient", "duplicate for transporter", "cash receipt",
        "receipt", "e-commerce operator", "payment receipt", "credit note"
    }
    for line in lines:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", line).strip().lower()
        if cleaned and cleaned not in skip_headers and len(line) >= 3 and not line.isdigit():
            return line[:40].strip()

    return "Unknown Vendor"


# ============================================================
# INVOICE / ORDER NUMBER
# ============================================================

def extract_order_or_invoice_number(text: str) -> str | None:
    """
    Extract order ID or invoice number using platform-specific and generic regex.
    - Amazon: [A-Z0-9]{3}-[0-9]{7}-[0-9]{7}
    - Flipkart / Meesho: Labeled under Invoice No, Order ID, Order No, etc.
    """
    # 1. Amazon-specific Order ID format: [A-Z0-9]{3}-[0-9]{7}-[0-9]{7}
    amazon_match = re.search(r"\b([A-Z0-9]{3}-[0-9]{7}-[0-9]{7})\b", text)
    if amazon_match:
        return amazon_match.group(1)

    # 2. Flipkart / Meesho / General labeled order and invoice patterns
    labeled_patterns = [
        # Labeled Invoice No / Number
        r"(?:Invoice\s*(?:No\.?|Number|#)|Inv\s*(?:No\.?|#)|Tax\s*Invoice\s*(?:No\.?|#))\s*[:\-\s#]\s*([A-Za-z0-9][A-Za-z0-9\-_/]{2,})",
        # Labeled Order ID / Number / Meesho Sub-order
        r"(?:Order\s*(?:ID|Id|No\.?|Number|#)|Sub-?Order\s*(?:ID|Id|No\.?))\s*[:\-\s#]\s*([A-Za-z0-9][A-Za-z0-9\-_/]{2,})",
        # Flipkart Order ID standalone pattern: OD followed by 16-20 digits
        r"\b(OD[0-9]{16,20})\b",
        # Meesho specific pattern if prefixed
        r"\b(MSH-[A-Za-z0-9\-_]+)\b",
    ]

    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            clean_id = match.group(1).strip(" .,:;-_#")
            if clean_id:
                return clean_id

    # 3. Fallback generic pattern
    generic_match = re.search(r"(?:Invoice|Order)\s*[:\-\s#]\s*([A-Za-z0-9\-_/]{3,})", text, re.IGNORECASE)
    if generic_match:
        return generic_match.group(1).strip(" .,:;-_#")

    return None


# ============================================================
# SEPARATE ORDER NUMBER (PO / Reference)
# ============================================================

def extract_order_number(text: str) -> str | None:
    """
    Extract an explicit purchase-order / reference number separate from the invoice number.
    Returns None if not found.
    """
    patterns = [
        r"(?:P\.?O\.?\s*(?:Number|No\.?|#)|Purchase\s*Order\s*(?:No\.?|Number|#)|Reference\s*(?:No\.?|Number|#))\s*[:\-\s#]\s*([A-Za-z0-9][A-Za-z0-9\-_/]{1,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip(" .,:;-_#")
            if val:
                return val
    return None


# ============================================================
# GRAND-TOTAL EXTRACTION HELPERS
# ============================================================

# Currency amount (Indian & Western formats): 1,538.00 | 1,12,500.00 | 499 | 12345.5
_NUM = (
    r"(?:[0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?"
    r"|[0-9]+(?:\.[0-9]{1,2})?)"
)
# Amount that MUST have decimals (used when a value sits on the line below its label,
# so table row numbers like "1" or "2" are never mistaken for money)
_NUM_DEC = r"(?:[0-9]{1,3}(?:,[0-9]{2,3})*\.[0-9]{1,2}|[0-9]+\.[0-9]{1,2})"
_CUR = r"(?:₹|Rs\.?|INR)"

# An amount inside a line; ignores percentages such as "9%" or "18.00 %"
_AMOUNT_RE = re.compile(rf"{_CUR}?[ \t]*({_NUM})(?![0-9.,]*[ \t]*%)", re.IGNORECASE)
# A whole line that is just a money value (value printed under its label)
_VALUE_ONLY_LINE_RE = re.compile(
    rf"^\s*(?:{_CUR}\s*{_NUM}|{_NUM_DEC})\s*$", re.IGNORECASE
)

# Labels that ALWAYS mean "this is a tax / non-payable component row".
_HARD_TAX_RE = re.compile(
    r"\b(?:CGST|SGST|IGST|UGST|UTGST|Tax\s+Amount|Tax\s+Rate|Total\s+Tax|Tax\s+Total"
    r"|Taxable|HSN|SAC\s*Code)\b",
    re.IGNORECASE,
)

# Minor components / non-final rows. Excluded unless the line also carries a
# definitive grand-total label (e.g. "Amount Payable (incl. shipping)").
_SOFT_COMPONENT_RE = re.compile(
    r"\b(?:GST\s*@|Cess|Sub\s*-?\s*Total|Total\s+(?:Qty|Quantity|Items?|Discount)"
    r"|(?:Service|Delivery|Handling|Convenience|Shipping|Packaging|Packing|Platform|Gift\s*Wrap|COD)"
    r"\s+(?:Tax|Fee|Fees|Charge|Charges)|Shipping|Discount|Round(?:ing)?\s*Off)\b",
    re.IGNORECASE,
)

# Definitive final-summary labels.
_GRAND_LABEL_RE = re.compile(
    r"\b(?:Invoice\s+Value|Grand\s+Total|Invoice\s+Total|Total\s+Amount\s+(?:Due|Payable)"
    r"|Total\s+Payable|Amount\s+(?:Due|Payable)|Net\s+Payable)\b",
    re.IGNORECASE,
)

# Label tiers, most reliable first.
_TOTAL_LABEL_TIERS = [
    r"Invoice\s+Value",
    r"Total\s+(?:Amount\s+(?:Due|Payable)|Payable)",
    r"(?:Grand\s+Total|Invoice\s+Total)",
    r"(?:Amount\s+Due|Amount\s+Payable|Net\s+Payable)",
    r"Total\s+Amount",
    # Bare "TOTAL" (e.g. Amazon: "TOTAL: ₹381.20 ₹2,499.00" = tax total, gross total)
    r"(?<![A-Za-z])Total(?![A-Za-z])",
]


def _is_excluded_line(line: str) -> bool:
    """True if the line is a tax / fee / minor-component row."""
    if _HARD_TAX_RE.search(line):
        return True
    if _SOFT_COMPONENT_RE.search(line) and not _GRAND_LABEL_RE.search(line):
        return True
    return False


def _sanitise(raw: str) -> str:
    """
    Remove tax / fee sub-rows. PDF extraction often puts a label and its value
    on separate lines, so value-only lines directly after a removed label are
    dropped too (otherwise an orphaned tax value could attach to the next label).
    """
    kept: list[str] = []
    drop_orphans = False
    for line in raw.splitlines():
        if _is_excluded_line(line):
            drop_orphans = True
            continue
        if drop_orphans and _VALUE_ONLY_LINE_RE.match(line):
            continue
        drop_orphans = False
        kept.append(line)
    return "\n".join(kept)


def _amounts_for_label(lines: list[str], label_pattern: str) -> list[float]:
    """
    Find the money value belonging to each occurrence of a label.
      - Same line: take the LAST amount after the label. On summary rows such as
        "TOTAL: ₹381.20 ₹2,499.00" the final column is the gross total.
      - Next line: only if the label line ends right after the label and the next
        line is nothing but a money value (must have a decimal part or a currency
        symbol, so row numbers like "1" are ignored).
    """
    label_re = re.compile(label_pattern, re.IGNORECASE)
    found: list[float] = []
    for i, line in enumerate(lines):
        for m in label_re.finditer(line):
            rest = line[m.end():]
            same_line = [a.group(1) for a in _AMOUNT_RE.finditer(rest)]
            raw = None
            if same_line:
                raw = same_line[-1]
            elif not rest.strip(" \t:-") and i + 1 < len(lines) and _VALUE_ONLY_LINE_RE.match(lines[i + 1]):
                nxt = _AMOUNT_RE.search(lines[i + 1])
                raw = nxt.group(1) if nxt else None
            if raw:
                try:
                    val = float(raw.replace(",", ""))
                except ValueError:
                    continue
                if val > 0:
                    found.append(val)
    return found


def extract_grand_total(text: str) -> float | None:
    """
    Extract the final payable total (Grand Total / Invoice Value / Amount Due)
    while ignoring tax and minor component rows (CGST, SGST, IGST, Tax Amount,
    Tax Rate, shipping / handling fees, discounts, sub-totals, etc.).

    Strategy:
      1. Sanitise: drop every tax/fee/minor-component line (and its orphaned
         value line) before any matching.
      2. Priority tiers: try definitive summary labels in order of reliability
         (Invoice Value > Total Amount Due > Grand Total > ... > bare Total).
         Within the first tier that yields values, return the highest value.
         On a row with several amounts the last (right-most) one is used.
      3. Smart fallback: gather amounts next to generic labels (Amount, Payable,
         Due) and return the highest one.
    """
    lines = _sanitise(text).splitlines()

    for label in _TOTAL_LABEL_TIERS:
        values = _amounts_for_label(lines, label)
        if values:
            # Highest value in the most reliable tier = final payable sum
            return round(max(values), 2)

    # Smart candidate fallback
    candidates = _amounts_for_label(lines, r"(?<![A-Za-z])(?:Amount|Payable|Due)(?![A-Za-z])")
    if candidates:
        return round(max(candidates), 2)

    return None


# ============================================================
# INVOICE DATE
# ============================================================

def extract_invoice_date(text: str) -> str | None:
    """
    Extract invoice or order date.
    Returns ISO YYYY-MM-DD string, or None if not found.
    """
    date_patterns = [
        # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        r"(?:Invoice\s*Date|Order\s*Date|Date\s*of\s*Invoice|Date|Dated)\s*[:\-\s]*\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
        # YYYY-MM-DD
        r"(?:Invoice\s*Date|Order\s*Date|Date)\s*[:\-\s]*\s*([0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2})",
        # DD Month YYYY (e.g. 15 Oct 2024 or 15 October 2024)
        r"(?:Invoice\s*Date|Order\s*Date|Date)\s*[:\-\s]*\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_date = match.group(1).strip()
            clean_date = raw_date.replace(".", "/").replace("-", "/")
            parts = clean_date.split("/")
            if len(parts) == 3 and len(parts[0]) <= 2 and len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            return raw_date

    return None


# ============================================================
# DUE DATE
# ============================================================

def extract_due_date(text: str) -> str | None:
    """
    Extract the payment due date. Returns ISO YYYY-MM-DD string, or None.
    """
    patterns = [
        r"(?:Due\s*Date|Payment\s*Due|Pay\s*By|Due\s*By)\s*[:\-\s]*\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
        r"(?:Due\s*Date|Payment\s*Due|Pay\s*By|Due\s*By)\s*[:\-\s]*\s*([0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2})",
        r"(?:Due\s*Date|Payment\s*Due|Pay\s*By|Due\s*By)\s*[:\-\s]*\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_date = match.group(1).strip()
            clean_date = raw_date.replace(".", "/").replace("-", "/")
            parts = clean_date.split("/")
            if len(parts) == 3 and len(parts[0]) <= 2 and len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            return raw_date
    return None


# ============================================================
# CURRENCY
# ============================================================

def extract_currency(text: str) -> str:
    """
    Detect the ISO 4217 currency code from the invoice text.
    Defaults to 'INR' if none detected.
    """
    if re.search(r"\bUSD\b|\$(?!\s*[0-9]*\s*(?:crore|lakh|k\b))", text, re.IGNORECASE):
        return "USD"
    if re.search(r"\bEUR\b|€", text):
        return "EUR"
    if re.search(r"\bGBP\b|£", text):
        return "GBP"
    if re.search(r"\bAED\b", text, re.IGNORECASE):
        return "AED"
    if re.search(r"\bSGD\b", text, re.IGNORECASE):
        return "SGD"
    # INR indicators: ₹ symbol, Rs., INR keyword
    if re.search(r"₹|Rs\.?|INR\b", text, re.IGNORECASE):
        return "INR"
    return "INR"


# ============================================================
# SUBTOTAL
# ============================================================

def extract_subtotal(text: str) -> float | None:
    """
    Extract the subtotal / item total (before taxes & shipping).
    Returns None if not found.
    """
    patterns = [
        r"(?:Sub\s*[-]?\s*Total|Item\s+Total|Taxable\s+(?:Value|Amount)|Net\s+Amount)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return round(float(match.group(1).replace(",", "")), 2)
            except ValueError:
                continue
    return None


# ============================================================
# TAX AMOUNT (TOTAL GST)
# ============================================================

def extract_tax_amount(text: str) -> float | None:
    """
    Extract total tax / GST amount paid.
    Returns None if not found.
    """
    patterns = [
        r"(?:Total\s+Tax|Tax\s+Amount|Tax\s+Total|Total\s+GST|GST\s+Total|Total\s+GST\s+Amount)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return round(float(match.group(1).replace(",", "")), 2)
            except ValueError:
                continue

    # Fallback: sum up individual CGST + SGST amounts if no total tax line found
    tax_breakup = extract_tax_breakup(text)
    if tax_breakup:
        total = sum(v for v in tax_breakup.values() if isinstance(v, (int, float)))
        if total > 0:
            return round(total, 2)

    return None


# ============================================================
# TAX BREAKUP (CGST / SGST / IGST)
# ============================================================

def extract_tax_breakup(text: str) -> dict | None:
    """
    Extract individual GST component amounts (CGST, SGST, IGST, UGST).
    Returns a dict like {"CGST_9": 45.0, "SGST_9": 45.0} or None if none found.
    Keys are formatted as "COMPONENT_RATE" where rate is the percentage.
    """
    result: dict = {}

    # Pattern: "CGST @ 9% : Rs. 45.00" or "CGST (9%) 45.00" or "CGST 9% 45.00"
    gst_pattern = re.compile(
        r"\b(CGST|SGST|IGST|UGST|UTGST)\b"
        r"(?:\s*[@(]?\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*[):]?)?"
        r"\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        re.IGNORECASE,
    )

    for match in gst_pattern.finditer(text):
        component = match.group(1).upper()
        rate = match.group(2)        # may be None
        amount_str = match.group(3)
        try:
            amount = float(amount_str.replace(",", ""))
        except (ValueError, AttributeError):
            continue
        if amount <= 0:
            continue
        key = f"{component}_{rate}" if rate else component
        # If the same key appears multiple times, accumulate (multi-line invoices)
        result[key] = round(result.get(key, 0.0) + amount, 2)

    return result if result else None


# ============================================================
# DISCOUNT
# ============================================================

def extract_discount(text: str) -> float | None:
    """
    Extract discount amount. Returns None if not found.
    """
    patterns = [
        r"(?:Discount|Coupon\s*Discount|Promo\s*Discount|Total\s+Discount)\s*[:\-]?\s*(?:₹|Rs\.?|INR|-)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                if val > 0:
                    return round(val, 2)
            except ValueError:
                continue
    return None


# ============================================================
# SHIPPING CHARGES
# ============================================================

def extract_shipping_charges(text: str) -> float | None:
    """
    Extract shipping / delivery / handling charges. Returns None if not found.
    """
    patterns = [
        r"(?:Shipping\s*(?:Charges?|Fee|Fees|Cost)?|Delivery\s*(?:Charges?|Fee|Fees|Cost)?|Handling\s*(?:Charges?|Fee|Fees)?|Freight)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                if val > 0:
                    return round(val, 2)
            except ValueError:
                continue
    return None


# ============================================================
# PAYMENT STATUS / METHOD
# ============================================================

def extract_payment_status_or_method(text: str) -> str | None:
    """
    Extract payment status (Paid, Unpaid, Pending) or method (COD, UPI, Card, etc.).
    Returns None if not found.
    """
    text_lower = text.lower()

    # Payment status keywords
    if re.search(r"\bpaid\b", text_lower):
        return "Paid"
    if re.search(r"\bunpaid\b", text_lower):
        return "Unpaid"
    if re.search(r"\bpending\b", text_lower):
        return "Pending"

    # Payment method keywords
    method_patterns = [
        (r"\bcod\b|cash\s*on\s*delivery", "COD"),
        (r"\bupi\b", "UPI"),
        (r"\bnet\s*banking\b|netbanking", "Net Banking"),
        (r"\bdebit\s*card\b", "Debit Card"),
        (r"\bcredit\s*card\b", "Credit Card"),
        (r"\bwallet\b", "Wallet"),
        (r"\bneft\b|\brtgs\b|\bimps\b", "Bank Transfer"),
        (r"\bcheque\b|\bcheck\b", "Cheque"),
        (r"\bcash\b", "Cash"),
    ]
    for pattern, label in method_patterns:
        if re.search(pattern, text_lower):
            return label

    # Labeled extraction
    labeled_match = re.search(
        r"(?:Payment\s*(?:Method|Mode|Status|Terms?)|Mode\s*of\s*Payment)\s*[:\-]\s*([^\r\n]{2,30})",
        text,
        re.IGNORECASE,
    )
    if labeled_match:
        val = labeled_match.group(1).strip()
        if val:
            return val[:30]

    return None


# ============================================================
# LINE ITEMS
# ============================================================

def extract_line_items(text: str) -> list[dict] | None:
    """
    Extract line items from invoice text as a list of dicts with keys:
      description, quantity, unit_price, line_total
    Returns None if no items could be parsed.

    Handles patterns like:
      "Item Description   Qty   Unit Price   Total"
      "Wireless Mouse  1  Rs. 499.00  Rs. 499.00"
      "Item: X  Price: Rs. 499.00  Total: Rs. 499.00"
    """
    items: list[dict] = []

    # Pattern 1: Labeled "Item: X  Price: Rs. N  Total: Rs. N"
    labeled_re = re.compile(
        r"(?:Item|Product|Description)\s*:\s*(.+?)"
        r"(?:\s+(?:Qty|Quantity)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?))?"
        r"\s+(?:Unit\s*Price|Price|Rate)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?)"
        r"(?:\s+(?:Total|Amount|Line\s+Total)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?))?",
        re.IGNORECASE,
    )
    for m in labeled_re.finditer(text):
        try:
            desc = m.group(1).strip()
            qty_str = m.group(2)
            price_str = m.group(3)
            total_str = m.group(4)
            qty = float(qty_str) if qty_str else 1.0
            unit_price = float(price_str.replace(",", "")) if price_str else 0.0
            line_total = float(total_str.replace(",", "")) if total_str else round(qty * unit_price, 2)
            if desc and unit_price > 0:
                items.append({
                    "description": desc[:80],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                })
        except (ValueError, AttributeError):
            continue

    if items:
        return items

    # Pattern 2: Tabular lines — "Description  Qty  UnitPrice  Total" layout
    # Heuristic: look for lines with 2–4 numeric columns (qty, price, total)
    tabular_re = re.compile(
        r"^(.{3,40}?)\s{2,}"                       # description (at least 3 chars, then 2+ spaces)
        r"([0-9]+(?:\.[0-9]+)?)\s+"                # quantity
        r"(?:₹|Rs\.?|INR)?\s*([0-9,]+\.[0-9]{2})\s+"  # unit price (must have decimals)
        r"(?:₹|Rs\.?|INR)?\s*([0-9,]+\.[0-9]{2})",    # line total (must have decimals)
        re.IGNORECASE | re.MULTILINE,
    )
    for m in tabular_re.finditer(text):
        try:
            desc = m.group(1).strip()
            qty = float(m.group(2))
            unit_price = float(m.group(3).replace(",", ""))
            line_total = float(m.group(4).replace(",", ""))
            # Skip lines that are clearly summary rows
            if re.search(r"\b(?:total|grand|subtotal|tax|gst|cgst|sgst|igst|discount|shipping)\b", desc, re.IGNORECASE):
                continue
            if desc and unit_price > 0:
                items.append({
                    "description": desc[:80],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                })
        except (ValueError, AttributeError):
            continue

    return items if items else None


# ============================================================
# MAIN PARSER ENTRY POINT
# ============================================================

def parse_invoice_pdf(file_bytes: bytes) -> dict:
    """
    Parses PDF bytes to extract all invoice fields with graceful null/fallback
    handling. Never raises — always returns a dict with a 'status' key.

    Extracted fields:
      vendor_name, invoice_number, invoice_date, total_amount, currency,
      tax_amount, subtotal, tax_breakup, discount, shipping_charges,
      due_date, order_number, payment_status_or_method, line_items,
      status, error_message
    """

    # Build a base "failed" response with all fields set to their safe defaults
    _null_response = {
        "vendor_name": None,
        "invoice_number": None,
        "invoice_date": None,
        "total_amount": None,
        "currency": "INR",
        "tax_amount": None,
        "subtotal": None,
        "tax_breakup": None,
        "discount": None,
        "shipping_charges": None,
        "due_date": None,
        "order_number": None,
        "payment_status_or_method": None,
        "line_items": None,
        "status": "Failed",
        "error_message": None,
    }

    try:
        reader = PdfReader(io.BytesIO(file_bytes))

        if len(reader.pages) == 0:
            return {
                **_null_response,
                "vendor_name": "Unknown Vendor",
                "invoice_number": "N/A",
                "invoice_date": "N/A",
                "total_amount": 0.0,
                "error_message": "PDF contains no pages.",
            }

        extracted_text = ""
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            except Exception:
                # Skip unreadable pages rather than failing the whole parse
                continue

        if not extracted_text or not extracted_text.strip():
            return {
                **_null_response,
                "vendor_name": "Unknown Vendor",
                "invoice_number": "N/A",
                "invoice_date": "N/A",
                "total_amount": 0.0,
                "error_message": "PDF has an empty text layer or is a scanned image without readable text.",
            }

        # --- Field extraction (each wrapped so one failure won't crash the rest) ---

        def _safe(fn, *args, default=None):
            """Call fn(*args) and return default on any exception."""
            try:
                return fn(*args)
            except Exception:
                return default

        vendor_name             = _safe(extract_vendor_name,              extracted_text, default="Unknown Vendor")
        invoice_number          = _safe(extract_order_or_invoice_number,  extracted_text)
        invoice_date            = _safe(extract_invoice_date,             extracted_text)
        total_amount            = _safe(extract_grand_total,              extracted_text)
        currency                = _safe(extract_currency,                 extracted_text, default="INR")
        tax_amount              = _safe(extract_tax_amount,               extracted_text)
        subtotal                = _safe(extract_subtotal,                 extracted_text)
        tax_breakup             = _safe(extract_tax_breakup,              extracted_text)
        discount                = _safe(extract_discount,                 extracted_text)
        shipping_charges        = _safe(extract_shipping_charges,         extracted_text)
        due_date                = _safe(extract_due_date,                 extracted_text)
        order_number            = _safe(extract_order_number,             extracted_text)
        payment_status_or_method = _safe(extract_payment_status_or_method, extracted_text)
        line_items              = _safe(extract_line_items,               extracted_text)

        # If total_amount could not be found, the invoice is not processable
        if total_amount is None:
            return {
                **_null_response,
                "vendor_name": vendor_name,
                "invoice_number": invoice_number or "N/A",
                "invoice_date": invoice_date or "N/A",
                "total_amount": 0.0,
                "currency": currency,
                "tax_amount": tax_amount,
                "subtotal": subtotal,
                "tax_breakup": tax_breakup,
                "discount": discount,
                "shipping_charges": shipping_charges,
                "due_date": due_date,
                "order_number": order_number,
                "payment_status_or_method": payment_status_or_method,
                "line_items": line_items,
                "error_message": "Pattern matching failed: unable to locate Grand Total or Amount Due in invoice.",
            }

        # Auto-generate invoice number if none was found but total was
        if not invoice_number:
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "vendor_name": vendor_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date or datetime.now().strftime("%Y-%m-%d"),
            "total_amount": total_amount,
            "currency": currency,
            "tax_amount": tax_amount,
            "subtotal": subtotal,
            "tax_breakup": tax_breakup,
            "discount": discount,
            "shipping_charges": shipping_charges,
            "due_date": due_date,
            "order_number": order_number,
            "payment_status_or_method": payment_status_or_method,
            "line_items": line_items,
            "status": "Processed",
            "error_message": None,
        }

    except Exception as e:
        # Catch-all: never crash the backend
        return {
            **_null_response,
            "vendor_name": "Parsing Error",
            "invoice_number": "N/A",
            "invoice_date": "N/A",
            "total_amount": 0.0,
            "error_message": f"Failed to parse invoice PDF: {str(e)}",
        }
