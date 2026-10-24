import io
import re
from datetime import datetime
from pypdf import PdfReader


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


# ---------------------------------------------------------------------- #
# Grand-total extraction helpers                                           #
# ---------------------------------------------------------------------- #

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


def extract_invoice_date(text: str) -> str:
    """
    Extract invoice or order date. Fallback to current date (YYYY-MM-DD).
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

    return datetime.now().strftime("%Y-%m-%d")


def parse_invoice_pdf(file_bytes: bytes) -> dict:
    """
    Parses PDF bytes to extract vendor name, invoice/order number, date, and grand total.
    Handles e-commerce invoices (Amazon, Flipkart, Meesho, etc.) and provides robust
    fallback and error resilience.
    """
    try:
        # Read PDF binary stream from memory
        reader = PdfReader(io.BytesIO(file_bytes))

        if len(reader.pages) == 0:
            return {
                "vendor_name": "Unknown Vendor",
                "invoice_number": "N/A",
                "invoice_date": "N/A",
                "total_amount": 0.0,
                "currency": "₹",
                "status": "Failed",
                "error_message": "PDF contains no pages."
            }

        extracted_text = ""
        # Loop through pages and extract text
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        # Check for empty text layer (scanned or image-only PDF)
        if not extracted_text or not extracted_text.strip():
            return {
                "vendor_name": "Unknown Vendor",
                "invoice_number": "N/A",
                "invoice_date": "N/A",
                "total_amount": 0.0,
                "currency": "₹",
                "status": "Failed",
                "error_message": "PDF has an empty text layer or is a scanned image without readable text."
            }

        # 1. Vendor Recognition
        vendor_name = extract_vendor_name(extracted_text)

        # 2. Platform-Specific Order / Invoice Number
        invoice_number = extract_order_or_invoice_number(extracted_text)

        # 3. Robust Grand Total Extraction
        total_amount = extract_grand_total(extracted_text)

        # 4. Invoice Date Extraction
        invoice_date = extract_invoice_date(extracted_text)

        # 5. Check if pattern matching failed
        if total_amount is None:
            return {
                "vendor_name": vendor_name,
                "invoice_number": invoice_number or "N/A",
                "invoice_date": invoice_date or "N/A",
                "total_amount": 0.0,
                "currency": "₹",
                "status": "Failed",
                "error_message": "Pattern matching failed: unable to locate Grand Total or Amount Due in invoice."
            }

        # If invoice number wasn't found but total was, provide an auto-generated fallback ID
        if not invoice_number:
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "vendor_name": vendor_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
            "currency": "₹",
            "status": "Processed",
            "error_message": None
        }

    except Exception as e:
        # Gracefully catch all parsing exceptions rather than crashing backend
        return {
            "vendor_name": "Parsing Error",
            "invoice_number": "N/A",
            "invoice_date": "N/A",
            "total_amount": 0.0,
            "currency": "₹",
            "status": "Failed",
            "error_message": f"Failed to parse invoice PDF: {str(e)}"
        }