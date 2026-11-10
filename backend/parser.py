import io
import re
from datetime import datetime, date
from pypdf import PdfReader


# ============================================================
# VENDOR DETECTION
# ============================================================

def extract_vendor_name(text: str) -> str | None:
    """
    Dynamically recognize vendors from extracted invoice text.
    Detects major e-commerce platforms like Amazon India, Flipkart, and Meesho,
    plus common quick-commerce/retail services and labeled seller lines.
    Returns None if no vendor can be identified.
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

    return None


# ============================================================
# INVOICE NUMBER (strict — never the Amazon order ID)
# ============================================================

# The (?![A-Za-z]) guard stops the label from matching inside longer words, and
# values are read from the same line only (or the next line if the label ends its line).
_INV_LABEL = (
    r"(?:Tax\s+Invoice|Invoice|Inv\.?)\s*"
    r"(?:Number|Num\.?|No\.?|#)(?![A-Za-z])"
)
_INV_VALUE = r"([A-Za-z0-9][A-Za-z0-9\-_/]{2,})"
_AMAZON_ORDER_ID_RE = re.compile(r"[A-Z0-9]{3}-[0-9]{7}-[0-9]{7}")


def _valid_invoice_candidate(candidate: str) -> bool:
    candidate = candidate.strip(" .,:;-_#")
    if len(candidate) < 3:
        return False
    # Amazon order IDs (XXX-1234567-1234567) belong to order_number only
    if _AMAZON_ORDER_ID_RE.fullmatch(candidate):
        return False
    # A real invoice number always contains at least one digit
    if not re.search(r"\d", candidate):
        return False
    return True


def extract_invoice_number(text: str) -> str | None:
    """
    Extract the TRUE invoice number using strict label matching.

    Matches "Invoice Number", "Invoice No.", "Tax Invoice No.", "Invoice #" etc.
    "Invoice Details", "Invoice Date" and "Invoice Value" are NOT labels for the
    invoice number and are never matched.

    Amazon's XXX-1234567-1234567 order-ID pattern is explicitly excluded here;
    it belongs exclusively in extract_order_number().
    Returns None if no labelled invoice number is found.
    """
    # Pass 1: value on the same line as the label (horizontal whitespace only,
    # so we never jump to the next line by accident).
    same_line = re.compile(
        rf"{_INV_LABEL}[ \t]*[:\-#]*[ \t]*{_INV_VALUE}", re.IGNORECASE
    )
    for m in same_line.finditer(text):
        candidate = m.group(1).strip(" .,:;-_#")
        if _valid_invoice_candidate(candidate):
            return candidate

    # Pass 2: label at the end of a line, value on the following line.
    next_line = re.compile(
        rf"{_INV_LABEL}[ \t]*[:\-#]*[ \t]*\r?\n[ \t]*{_INV_VALUE}", re.IGNORECASE
    )
    for m in next_line.finditer(text):
        candidate = m.group(1).strip(" .,:;-_#")
        if _valid_invoice_candidate(candidate):
            return candidate

    return None


# ============================================================
# ORDER NUMBER (PO / Reference / Amazon Order ID)
# ============================================================

def extract_order_number(text: str) -> str | None:
    """
    Extract the order number / purchase-order / reference number.

    Matches:
      - Amazon order IDs: XXX-1234567-1234567
      - Flipkart OD-prefixed IDs
      - Meesho MSH- prefixed IDs
      - Labels: "Order ID", "Order No.", "PO Number", "Reference No.", etc.
    Returns None if not found.
    """
    amazon_match = re.search(r"\b([A-Z0-9]{3}-[0-9]{7}-[0-9]{7})\b", text)
    if amazon_match:
        return amazon_match.group(1)

    flipkart_match = re.search(r"\b(OD[0-9]{16,20})\b", text)
    if flipkart_match:
        return flipkart_match.group(1)

    meesho_match = re.search(r"\b(MSH-[A-Za-z0-9\-_]+)\b", text)
    if meesho_match:
        return meesho_match.group(1)

    labeled_patterns = [
        r"(?:Order\s*(?:ID|Id|Number|No\.?|#)|Sub-?Order\s*(?:ID|Id|Number|No\.?))(?![A-Za-z])\s*[:\-\s#]*([A-Za-z0-9][A-Za-z0-9\-_/]{2,})",
        r"(?:P\.?O\.?\s*(?:Number|No\.?|#)|Purchase\s*Order\s*(?:Number|No\.?|#))(?![A-Za-z])\s*[:\-\s#]*([A-Za-z0-9][A-Za-z0-9\-_/]{1,})",
        r"(?:Reference\s*(?:Number|No\.?|#))(?![A-Za-z])\s*[:\-\s#]*([A-Za-z0-9][A-Za-z0-9\-_/]{1,})",
    ]

    for pattern in labeled_patterns:
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
# so table row numbers like "1" or "2" are never mistaken for money).
_NUM_DEC = r"(?:[0-9]{1,3}(?:,[0-9]{2,3})*\.[0-9]{1,2}|[0-9]+\.[0-9]{1,2})"
_CUR = r"(?:₹|Rs\.?|INR)"

_AMOUNT_RE = re.compile(
    rf"{_CUR}?[ \t]*({_NUM})(?![0-9.,]*[ \t]*%)",
    re.IGNORECASE,
)
_VALUE_ONLY_LINE_RE = re.compile(
    rf"^\s*(?:{_CUR}\s*{_NUM}|{_NUM_DEC})\s*$",
    re.IGNORECASE,
)

_HARD_TAX_RE = re.compile(
    r"\b(?:CGST|SGST|IGST|UGST|UTGST|Central\s+Tax|State\s+Tax|Integrated\s+Tax"
    r"|Tax\s+Amount|Tax\s+Rate|Total\s+Tax|Tax\s+Total"
    r"|Taxable|HSN|SAC\s*Code)\b",
    re.IGNORECASE,
)

_SOFT_COMPONENT_RE = re.compile(
    r"\b(?:GST\s*@|Cess|Sub\s*-?\s*Total|Total\s+(?:Qty|Quantity|Items?|Discount)"
    r"|(?:Service|Delivery|Handling|Convenience|Shipping|Packaging|Packing|Platform|Gift\s*Wrap|COD)"
    r"\s+(?:Tax|Fee|Fees|Charge|Charges)|Shipping|Discount|Round(?:ing)?\s*Off)\b",
    re.IGNORECASE,
)

_GRAND_LABEL_RE = re.compile(
    r"\b(?:Invoice\s+Value|Grand\s+Total|Invoice\s+Total|Total\s+Amount\s+(?:Due|Payable)"
    r"|Total\s+Payable|Amount\s+(?:Due|Payable)|Net\s+Payable)\b",
    re.IGNORECASE,
)

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
    dropped too.
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
      - Same line: take the LAST amount after the label.
      - Next line: only if the label line ends right after the label and the next
        line is nothing but a money value.
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
    while ignoring tax and minor component rows.

    1. Sanitise: drop every tax/fee/minor-component line.
    2. Priority tiers: Invoice Value > Total Amount Due > Grand Total > ... > bare Total.
    3. Fallback on generic Amount / Payable / Due labels.
    """
    lines = _sanitise(text).splitlines()

    for label in _TOTAL_LABEL_TIERS:
        values = _amounts_for_label(lines, label)
        if values:
            return round(max(values), 2)

    candidates = _amounts_for_label(lines, r"(?<![A-Za-z])(?:Amount|Payable|Due)(?![A-Za-z])")
    if candidates:
        return round(max(candidates), 2)

    return None


# ============================================================
# DATE PARSING HELPERS
# ============================================================

_DATE_FORMATS = [
    "%d/%m/%Y",   # 15/10/2024
    "%d-%m-%Y",   # 15-10-2024
    "%d/%m/%y",   # 15/10/24  → day-first assumed (Indian convention)
    "%d-%m-%y",   # 15-10-24
    "%d %b %Y",   # 15 Oct 2024
    "%d %B %Y",   # 15 October 2024
    "%Y-%m-%d",   # 2024-10-15 (ISO)
    "%Y/%m/%d",   # 2024/10/15
]


def _today() -> date:
    return date.today()


def _parse_date_str(raw: str) -> str | None:
    """
    Normalise a raw date string to YYYY-MM-DD.
    Tries every format in _DATE_FORMATS (day-first for ambiguous cases) and
    rejects future dates.
    """
    raw = raw.strip()
    normalised = raw.replace(".", "/")

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(normalised, fmt).date()
        except ValueError:
            try:
                parsed = datetime.strptime(raw, fmt).date()
            except ValueError:
                continue

        if parsed > _today():
            return None

        return parsed.strftime("%Y-%m-%d")

    return None


# ============================================================
# INVOICE DATE
# ============================================================

def extract_invoice_date(text: str) -> str | None:
    """
    Extract the invoice date from labelled fields.
      1. "Invoice Date" / "Date of Invoice" / "Dated"
      2. "Order Date" — soft fallback only.
    Returns a normalised YYYY-MM-DD string, or None.
    """
    _D1 = r"([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})"
    _D2 = r"([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})"
    _D3 = r"([0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2})"

    primary_labels = r"(?:Invoice\s*Date|Date\s*of\s*Invoice|Dated)"
    primary_patterns = [
        rf"(?:{primary_labels})\s*[:\-\s]*{_D1}",
        rf"(?:{primary_labels})\s*[:\-\s]*{_D2}",
        rf"(?:{primary_labels})\s*[:\-\s]*{_D3}",
    ]

    for pattern in primary_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result = _parse_date_str(m.group(1))
            if result:
                return result

    fallback_patterns = [
        rf"(?:Order\s*Date)\s*[:\-\s]*{_D1}",
        rf"(?:Order\s*Date)\s*[:\-\s]*{_D2}",
        rf"(?:Order\s*Date)\s*[:\-\s]*{_D3}",
    ]

    for pattern in fallback_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result = _parse_date_str(m.group(1))
            if result:
                return result

    return None


# ============================================================
# DUE DATE
# ============================================================

def extract_due_date(text: str) -> str | None:
    """
    Extract the payment due date from strict "Due Date" / "Payment Due" labels.
    Returns YYYY-MM-DD or None.
    """
    _D1 = r"([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})"
    _D2 = r"([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})"
    _D3 = r"([0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2})"

    label = r"(?:Due\s*Date|Payment\s*Due|Pay\s*By|Due\s*By)"
    patterns = [
        rf"(?:{label})\s*[:\-\s]*{_D1}",
        rf"(?:{label})\s*[:\-\s]*{_D2}",
        rf"(?:{label})\s*[:\-\s]*{_D3}",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result = _parse_date_str(m.group(1))
            if result:
                return result

    return None


# ============================================================
# CURRENCY
# ============================================================

def extract_currency(text: str) -> str | None:
    """
    Detect the ISO 4217 currency code from the invoice text.
    Returns None if no currency symbol or code is explicitly found.
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
    # "Rs" must not be the tail of another word (e.g. "Customers", "Registration")
    if re.search(r"₹|(?<![A-Za-z])Rs\.?(?=[\s\d])|\bINR\b", text, re.IGNORECASE):
        return "INR"
    return None


# ============================================================
# MONETARY VALUE HELPER
# ============================================================

_MONETARY_RE = re.compile(
    rf"(?:{_CUR}[ \t]*({_NUM_DEC})|[ \t]*({_NUM_DEC})[ \t]*(?![0-9.,]*[ \t]*%))",
    re.IGNORECASE,
)


def _extract_monetary_for_label(text: str, label_pattern: str) -> float | None:
    """
    Find a money value on the same line as label_pattern (or on the next line
    if the label line has no trailing content). Skips percentages.
    """
    label_re = re.compile(label_pattern, re.IGNORECASE)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = label_re.search(line)
        if not m:
            continue
        rest = line[m.end():]
        amounts = _AMOUNT_RE.findall(rest)
        for raw in amounts:
            if re.search(rf"{re.escape(raw)}[ \t]*%", rest):
                continue
            if "." in raw or re.search(_CUR, line, re.IGNORECASE):
                try:
                    val = float(raw.replace(",", ""))
                    if val > 0:
                        return round(val, 2)
                except ValueError:
                    continue
        if not rest.strip(" \t:-") and i + 1 < len(lines):
            nxt_line = lines[i + 1]
            if _VALUE_ONLY_LINE_RE.match(nxt_line):
                nxt = _AMOUNT_RE.search(nxt_line)
                if nxt:
                    try:
                        val = float(nxt.group(1).replace(",", ""))
                        if val > 0:
                            return round(val, 2)
                    except ValueError:
                        pass
    return None


# ============================================================
# SUBTOTAL
# ============================================================

def extract_subtotal(text: str) -> float | None:
    """
    Extract the subtotal / item total (before taxes & shipping).
    Returns None if not found.
    """
    label = r"(?:Sub\s*[-]?\s*Total|Item\s+Total|Taxable\s+(?:Value|Amount)|Net\s+Amount)"
    return _extract_monetary_for_label(text, label)


# ============================================================
# TAX AMOUNT & BREAKUP
# ============================================================

# Money token that REQUIRES two decimals (so serial numbers, HSN codes, quantities
# and percentages are never captured) and supports thousands separators:
#   ₹15.10 | ₹7,169.34 | 1,12,500.00 | Rs. 45.82
# The old pattern used \d{1,6}\.\d{2} which could not match "7,169.34".
_TAX_MONEY_RE = re.compile(
    r"(?:₹|Rs\.?|INR)?[ \t]*"
    r"(\d{1,3}(?:,\d{2,3})+\.\d{2}|\d+\.\d{2})"
    r"(?![\d,]*[ \t]*%)",
    re.IGNORECASE,
)


def _money_values(s: str) -> list[float]:
    """All decimal money amounts in a string, in order (percentages excluded)."""
    out: list[float] = []
    for m in _TAX_MONEY_RE.finditer(s):
        try:
            out.append(round(float(m.group(1).replace(",", "")), 2))
        except ValueError:
            continue
    return out


# Explicit summary-level tax labels, most specific first.
_TAX_LABELS = [
    r"\b(?:Total\s+)?(?:Central\s+Tax|Central\s+GST|CGST)\s*(?:\+|\band\b|&)\s*(?:State\s+Tax|State\s+GST|UT\s+Tax|UTGST|SGST)(?:\s+(?:Amount|Amt))?",
    r"\bTotal\s+Tax(?:es|\s+Amount|\s+Value)?(?:\s*\(\s*GST\s*\))?(?!\s*(?:able|Rate|%|Percentage))",
    r"\bTotal\s+GST(?:\s+Amount|\s+Value)?(?!\s*(?:Rate|%|Percentage))",
    r"\bTotal\s+(?:Integrated\s+Tax|IGST)(?:\s+(?:Amount|Amt))?",
    r"\b(?:GST|Tax)\s+Total\b",
    r"\bTax\s+Payable\b",
    r"\bGST\s+Amount\b",
    r"\bTax\s+Amount\b(?!\s*(?:able|Rate|%|Percentage))",
]

# "TOTAL: ₹15.10 ₹99.00"  (Amazon style: <total tax> <total amount>)
# "Total  ₹100.00 ₹18.00 ₹118.00" (net, tax, gross)
_TOTAL_ROW_RE = re.compile(
    r"^\s*(?:Grand\s+)?Total\s*:?[ \t]*(?=₹|Rs|INR|\d)", re.IGNORECASE
)

_TAX_COMPONENT_RE = re.compile(
    r"\b(?P<comp>CGST|SGST|IGST|UTGST|UGST"
    r"|Central\s+Tax(?:\s*\(CGST\))?|Central\s+GST"
    r"|State\s+Tax(?:\s*\(SGST\))?|State\s+GST"
    r"|Integrated\s+Tax(?:\s*\(IGST\))?|Integrated\s+GST"
    r"|Union\s+Territory\s+Tax|UT\s+Tax|UT\s+GST)\b"
    r"(?:[ \t]*(?:Amount|Amt))?"
    r"(?:[ \t]*(?:@|at|\()?[ \t]*(?P<rate>[0-9]+(?:\.[0-9]+)?)[ \t]*%[ \t]*[):]?)?"
    r"(?:[ \t]*(?:Amount|Amt|Tax))?"
    r"[ \t]*[:\-]?[ \t]*(?:₹|Rs\.?|INR|\$|€|£)?[ \t]*(?P<amt>[0-9,]+\.[0-9]{1,2})"
    r"(?![0-9.,]*[ \t]*%)",
    re.IGNORECASE,
)

_COMBINED_TAX_LABEL_RE = re.compile(
    r"\b(?:Total\s+)?(?:Central\s+Tax|Central\s+GST|CGST)\s*(?:\+|\band\b|\&)\s*(?:State\s+Tax|State\s+GST|UT\s+Tax|UTGST|SGST)(?:\s+(?:Amount|Amt))?\b",
    re.IGNORECASE,
)

_SUMMARY_COMPONENT_RE = re.compile(
    r"\bTotal\s+(?:CGST|SGST|IGST|UTGST|UGST|Central\s+Tax|State\s+Tax|Integrated\s+Tax)\b",
    re.IGNORECASE,
)


def _normalize_tax_component_name(comp: str) -> str:
    """Normalize extracted tax component to canonical GST key."""
    c = comp.upper()
    if "CENTRAL" in c or "CGST" in c:
        return "CGST"
    if "STATE" in c or "SGST" in c:
        return "SGST"
    if "INTEGRATED" in c or "IGST" in c:
        return "IGST"
    if "UTGST" in c or "UGST" in c or "UNION" in c or "UT " in c or "UT_" in c:
        return "UTGST"
    return comp.upper()


def extract_tax_breakup(text: str) -> dict | None:
    """
    Extract individual GST component amounts (CGST, SGST, IGST, UTGST).
    Returns e.g. {"CGST_9": 45.82, "SGST_9": 45.82} or {"IGST": 90.0}, or None.

    Only decimal amounts are accepted, so rates, serial numbers and HSN codes
    are never mistaken for tax amounts. Thousands separators ("7,169.34") work.
    If explicit "Total CGST" style summary lines exist, only those are used so
    item rows are not double counted.
    """
    result: dict = {}
    lines = text.splitlines()
    has_summary_components = bool(_SUMMARY_COMPONENT_RE.search(text))

    for line in lines:
        if _COMBINED_TAX_LABEL_RE.search(line):
            continue
        if has_summary_components and not _SUMMARY_COMPONENT_RE.search(line):
            continue

        for m in _TAX_COMPONENT_RE.finditer(line):
            component = _normalize_tax_component_name(m.group("comp"))
            rate = m.group("rate")
            try:
                amount = float(m.group("amt").replace(",", ""))
            except (ValueError, AttributeError):
                continue
            if amount <= 0:
                continue
            if rate:
                rf = float(rate)
                key = f"{component}_{int(rf) if rf.is_integer() else rf}"
            else:
                key = component
            result[key] = round(result.get(key, 0.0) + amount, 2)

    return result if result else None


def extract_tax_amount(
    text: str,
    _subtotal: float | None = None,
    _total_amount: float | None = None,
    _shipping: float | None = None,
    _discount: float | None = None,
) -> float | None:
    """
    Extract the TOTAL tax / GST amount paid.

    Strategy (first confident hit wins, bottom of the document scanned first
    because summary rows live there):

      1. Totals row  — "TOTAL: ₹15.10 ₹99.00" (Amazon) or "Total 100.00 18.00 118.00".
         The second-to-last amount on the row is the total tax and the last is the
         gross total. If total_amount is known the last amount must match it.
      2. Explicit label — "Total Tax", "Total GST", "Central Tax + State Tax",
         "Tax Amount", ... followed by a decimal amount on the same line (or on
         the next line when the label ends its line).
      3. Component sum — CGST + SGST / IGST / UTGST from extract_tax_breakup.
      4. Derivation — total − subtotal − shipping + discount (last resort).

    Candidates from steps 1-3 are rejected when subtotal and total are both known
    and the balance equation (±1.50) fails, so a wrong match can't win silently.
    """
    shipping = _shipping or 0.0
    discount = _discount or 0.0
    tol = 1.50

    def _balanced(tax: float) -> bool:
        if _subtotal is None or _total_amount is None or _total_amount <= 0:
            return True  # nothing to verify against
        return abs(round(_subtotal + tax + shipping - discount, 2) - _total_amount) <= tol

    lines = text.splitlines()
    n = len(lines)
    # Bottom 30% first, then the rest top-down
    bottom = max(0, int(n * 0.70))
    order = list(range(bottom, n)) + list(range(0, bottom))

    # ---- 1. Totals row ------------------------------------------------
    for i in order:
        line = lines[i]
        if not _TOTAL_ROW_RE.match(line):
            continue
        vals = _money_values(line)
        if len(vals) < 2:
            continue
        tax, gross = vals[-2], vals[-1]
        if tax <= 0 or tax >= gross:
            continue
        if _total_amount is not None and abs(gross - _total_amount) > tol:
            continue
        if _balanced(tax):
            return tax

    # ---- 2. Explicit tax labels ---------------------------------------
    for label in _TAX_LABELS:
        label_re = re.compile(label, re.IGNORECASE)
        for i in order:
            line = lines[i]
            m = label_re.search(line)
            if not m:
                continue
            vals = _money_values(line[m.end():])
            if not vals and not line[m.end():].strip(" \t:-") and i + 1 < n:
                if _VALUE_ONLY_LINE_RE.match(lines[i + 1]):
                    vals = _money_values(lines[i + 1])
            if not vals:
                continue
            tax = vals[0]
            if tax > 0 and _balanced(tax):
                return tax

    # ---- 3. Component sum ---------------------------------------------
    breakup = extract_tax_breakup(text)
    if breakup:
        comp_sum = round(sum(breakup.values()), 2)
        if comp_sum > 0 and _balanced(comp_sum):
            return comp_sum

    # ---- 4. Derivation -------------------------------------------------
    if _subtotal is not None and _total_amount is not None and _total_amount > _subtotal > 0:
        derived = round(_total_amount - _subtotal - shipping + discount, 2)
        if 0 < derived <= _subtotal * 0.5:
            return derived

    return None


# ============================================================
# DISCOUNT
# ============================================================

def extract_discount(text: str) -> float | None:
    """Extract discount amount. Returns None if not found."""
    label = r"(?:Discount|Coupon\s*Discount|Promo\s*Discount|Total\s+Discount)"
    return _extract_monetary_for_label(text, label)


# ============================================================
# SHIPPING CHARGES
# ============================================================

def extract_shipping_charges(text: str) -> float | None:
    """Extract shipping / delivery / handling charges. Returns None if not found."""
    label = (
        r"(?:Shipping\s*(?:Charges?|Fee|Fees|Cost)?"
        r"|Delivery\s*(?:Charges?|Fee|Fees|Cost)?"
        r"|Handling\s*(?:Charges?|Fee|Fees)?"
        r"|Freight)"
    )
    return _extract_monetary_for_label(text, label)


# ============================================================
# PAYMENT STATUS / METHOD
# ============================================================

def extract_payment_status_or_method(text: str) -> str | None:
    """
    Extract payment status (Paid, Unpaid, Pending) or method (COD, UPI, Card, etc.).
    Returns None if not found.
    """
    text_lower = text.lower()

    if re.search(r"\bunpaid\b", text_lower):
        return "Unpaid"
    if re.search(r"\bpaid\b", text_lower):
        return "Paid"
    if re.search(r"\bpending\b", text_lower):
        return "Pending"

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
    Extract line items as a list of dicts with keys:
      description, quantity, unit_price, line_total
    Returns None if no items could be parsed.
    """
    items: list[dict] = []

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
            unit_price = float(price_str.replace(",", "")) if price_str else None
            line_total = float(total_str.replace(",", "")) if total_str else (
                round(qty * unit_price, 2) if unit_price else None
            )
            if desc and unit_price and unit_price > 0:
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

    tabular_re = re.compile(
        r"^(.{3,40}?)\s{2,}"
        r"([0-9]+(?:\.[0-9]+)?)\s+"
        r"(?:₹|Rs\.?|INR)?[ \t]*([0-9,]+\.[0-9]{2})\s+"
        r"(?:₹|Rs\.?|INR)?[ \t]*([0-9,]+\.[0-9]{2})",
        re.IGNORECASE | re.MULTILINE,
    )
    for m in tabular_re.finditer(text):
        try:
            desc = m.group(1).strip()
            qty = float(m.group(2))
            unit_price = float(m.group(3).replace(",", ""))
            line_total = float(m.group(4).replace(",", ""))
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
# VALIDATION ENGINE
# ============================================================

# Standard Indian GST slabs (%)
_GST_SLABS = {0, 5, 12, 18, 28}


def validate_invoice(data: dict) -> dict:
    """
    Validate extracted invoice data and return a structured result.

    Checks:
      1. subtotal + tax_amount + shipping_charges - discount == total_amount (±1.50)
      2. sum(line_items[*].line_total) == subtotal (or total) when present (±1.50)
      3. total_amount > 0
      4. invoice_date valid and not in the future
      5. Tax rate matches standard GST slabs when stated

    Returns {"valid": bool, "missing_fields": [...], "validation_errors": [...]}.
    """
    missing_fields: list[str] = []
    validation_errors: list[str] = []

    core_fields = [
        ("vendor_name",   data.get("vendor_name")),
        ("invoice_number", data.get("invoice_number")),
        ("invoice_date",  data.get("invoice_date")),
        ("total_amount",  data.get("total_amount")),
        ("currency",      data.get("currency")),
    ]
    for field_name, value in core_fields:
        if value is None:
            missing_fields.append(field_name)

    def _to_float(v):
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    total_amount     = _to_float(data.get("total_amount"))
    subtotal         = _to_float(data.get("subtotal"))
    tax_amount       = _to_float(data.get("tax_amount"))
    shipping_charges = _to_float(data.get("shipping_charges"))
    discount         = _to_float(data.get("discount"))
    invoice_date     = data.get("invoice_date")
    line_items       = data.get("line_items")
    tax_breakup      = data.get("tax_breakup")

    if total_amount is not None:
        if total_amount <= 0:
            validation_errors.append(
                f"total_amount must be greater than 0 (got {total_amount})"
            )

    if (total_amount is not None and total_amount > 0
            and subtotal is not None
            and tax_amount is not None):
        shipping = shipping_charges or 0.0
        disc     = discount or 0.0
        expected = round(subtotal + tax_amount + shipping - disc, 2)
        tolerance = 1.50
        if abs(expected - total_amount) > tolerance:
            validation_errors.append(
                f"Balance mismatch: subtotal({subtotal}) + tax({tax_amount}) "
                f"+ shipping({shipping}) - discount({disc}) = {expected} "
                f"≠ total_amount({total_amount}) [tolerance ±{tolerance}]"
            )

    if line_items and subtotal is not None:
        try:
            items_sum = round(
                sum(float(item.get("line_total") or 0) for item in line_items), 2
            )
            tolerance = 1.50
            matches_subtotal = abs(items_sum - subtotal) <= tolerance
            matches_total = total_amount is not None and abs(items_sum - total_amount) <= tolerance
            if not matches_subtotal and not matches_total:
                validation_errors.append(
                    f"Line-items total ({items_sum}) does not match subtotal ({subtotal})"
                )
        except (TypeError, ValueError):
            pass

    if invoice_date is not None:
        try:
            parsed_inv_date = datetime.strptime(invoice_date, "%Y-%m-%d").date()
            if parsed_inv_date > _today():
                validation_errors.append(
                    f"invoice_date ({invoice_date}) is in the future"
                )
        except ValueError:
            validation_errors.append(
                f"invoice_date ({invoice_date}) is not a valid YYYY-MM-DD date"
            )

    if tax_breakup and subtotal and subtotal > 0:
        for key, amount in tax_breakup.items():
            parts = key.split("_", 1)
            if len(parts) == 2:
                try:
                    rate = float(parts[1])
                    if rate not in _GST_SLABS and (rate * 2) not in _GST_SLABS:
                        validation_errors.append(
                            f"Non-standard GST rate detected: {key} = {rate}% "
                            f"(standard slabs: {sorted(_GST_SLABS)})"
                        )
                except ValueError:
                    pass

    is_valid = not missing_fields and not validation_errors
    return {
        "valid": is_valid,
        "missing_fields": missing_fields,
        "validation_errors": validation_errors,
    }


# ============================================================
# MAIN PARSER ENTRY POINT
# ============================================================

def parse_invoice_text(extracted_text: str) -> dict:
    """
    Run every extractor on already-extracted text and validate the result.
    Split out of parse_invoice_pdf so the extraction logic can be unit-tested
    without a PDF file.
    """
    def _safe(fn, *args, default=None):
        try:
            return fn(*args)
        except Exception:
            return default

    vendor_name              = _safe(extract_vendor_name,              extracted_text)
    invoice_number           = _safe(extract_invoice_number,           extracted_text)
    invoice_date             = _safe(extract_invoice_date,             extracted_text)
    total_amount             = _safe(extract_grand_total,              extracted_text)
    currency                 = _safe(extract_currency,                 extracted_text)
    subtotal                 = _safe(extract_subtotal,                 extracted_text)
    discount                 = _safe(extract_discount,                 extracted_text)
    shipping_charges         = _safe(extract_shipping_charges,         extracted_text)
    tax_amount               = _safe(
        extract_tax_amount,
        extracted_text,
        subtotal,
        total_amount,
        shipping_charges,
        discount,
    )
    tax_breakup              = _safe(extract_tax_breakup,              extracted_text)
    due_date                 = _safe(extract_due_date,                 extracted_text)
    order_number             = _safe(extract_order_number,             extracted_text)
    payment_status_or_method = _safe(extract_payment_status_or_method, extracted_text)
    line_items               = _safe(extract_line_items,              extracted_text)

    extracted: dict = {
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
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
        "error_message": None,
    }

    if total_amount is None:
        return {
            **extracted,
            "status": "Needs Review",
            "error_message": (
                "Pattern matching failed: unable to locate Grand Total "
                "or Amount Due in invoice."
            ),
            "missing_fields": ["total_amount"],
            "validation_errors": [],
        }

    validation_result = validate_invoice(extracted)
    missing_fields    = validation_result["missing_fields"]
    validation_errors = validation_result["validation_errors"]

    return {
        **extracted,
        "status": "Needs Review" if (missing_fields or validation_errors) else "Extracted",
        "missing_fields": missing_fields,
        "validation_errors": validation_errors,
    }


def split_into_invoices(page_texts: list[str]) -> list[str]:
    """
    Group PDF pages into invoices. A page that carries its own labelled invoice
    number starts a new invoice; a page without one (e.g. a continuation page)
    is appended to the previous invoice.
    """
    segments: list[str] = []
    for text in page_texts:
        if segments and extract_invoice_number(text) is None:
            segments[-1] += "\n" + text
        else:
            segments.append(text)
    return segments


def parse_invoice_pdf(file_bytes: bytes) -> dict:
    """
    Parses PDF bytes to extract all invoice fields with strict null handling.
    Never raises — always returns a dict with a 'status' key.

    Status values:
      "Extracted"    — all core fields found and all validation checks pass
      "Needs Review" — a core field is missing or a validation check fails
      "Failed"       — PDF could not be read / has no text layer
      "Verified"     — set only after the user manually confirms in the UI
    """
    _null_response: dict = {
        "vendor_name": None,
        "invoice_number": None,
        "invoice_date": None,
        "total_amount": None,
        "currency": None,
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
        "missing_fields": [],
        "validation_errors": [],
    }

    try:
        reader = PdfReader(io.BytesIO(file_bytes))

        if len(reader.pages) == 0:
            return {**_null_response, "error_message": "PDF contains no pages."}

        page_texts: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text()
            except Exception:
                continue
            if text and text.strip():
                page_texts.append(text)

        if not page_texts:
            return {
                **_null_response,
                "error_message": (
                    "PDF has an empty text layer or is a scanned image "
                    "without readable text."
                ),
            }

        # A single PDF can contain several invoices (e.g. Amazon prints one page
        # per seller / per shipment). Parsing the concatenated text mixes fields
        # from different invoices — invoice number from page 1, total from page 2.
        # So split into invoices first and parse each one on its own.
        segments = split_into_invoices(page_texts)
        results = [parse_invoice_text(seg) for seg in segments]

        if len(results) == 1:
            return results[0]

        # Backward compatible: top-level fields describe the primary (highest
        # value) invoice; every invoice is available under "invoices".
        primary = max(results, key=lambda r: r.get("total_amount") or 0)
        return {
            **primary,
            "multiple_invoices": True,
            "invoices": results,
        }

    except Exception as e:
        return {
            **_null_response,
            "error_message": f"Failed to parse invoice PDF: {str(e)}",
        }