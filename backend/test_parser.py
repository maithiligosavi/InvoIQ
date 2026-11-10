import io
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pypdf import PdfWriter
import parser


def make_pdf(text: str) -> bytes:
    escaped_text = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    lines = escaped_text.splitlines()
    stream_content = "BT /F1 12 Tf 50 750 Td 14 TL "
    for line in lines:
        stream_content += f"({line}) Tj T* "
    stream_content += "ET"
    stream_len = len(stream_content.encode("utf-8", errors="replace"))

    pdf_template = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream_content}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000300 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
380
%%EOF"""
    return pdf_template.encode("latin1", errors="replace")


def run_tests():
    print("=== RUNNING DOCUFLOW PDF PARSER TESTS ===\n")

    # ----------------------------------------------------------------
    # Test 1: Amazon Invoice — order ID goes to order_number, NOT invoice_number
    # ----------------------------------------------------------------
    print("Test 1: Amazon Invoice with multiple item prices and Amazon order ID...")
    amazon_text = (
        "Tax Invoice / Bill of Supply\n"
        "Amazon Seller Services Private Limited\n"
        "Order Number: 408-1234567-1234567\n"
        "Date: 15.08.2024\n"
        "Item 1: Wireless Mouse  Price: Rs. 499.00  Total: Rs. 499.00\n"
        "Item 2: USB Hub  Price: Rs. 999.00  Total: Rs. 999.00\n"
        "Shipping Charges: Rs. 40.00\n"
        "Item Total: Rs. 1498.00\n"
        "Grand Total: Rs. 1538.00"
    )
    res_amazon = parser.parse_invoice_pdf(make_pdf(amazon_text))
    print("  Result:", res_amazon)
    # Amazon XXX-NNN-NNN pattern → order_number, never invoice_number
    assert res_amazon["order_number"] == "408-1234567-1234567", \
        f"Expected order_number=408-1234567-1234567, got {res_amazon['order_number']}"
    assert res_amazon["invoice_number"] is None, \
        f"Expected invoice_number=None (no labelled inv no.), got {res_amazon['invoice_number']}"
    assert res_amazon["vendor_name"] == "Amazon India", \
        f"Expected Amazon India, got {res_amazon['vendor_name']}"
    assert res_amazon["total_amount"] == 1538.0, \
        f"Expected 1538.0, got {res_amazon['total_amount']}"
    # Status must be "Needs Review" because invoice_number is missing
    assert res_amazon["status"] == "Needs Review", \
        f"Expected Needs Review (invoice_number missing), got {res_amazon['status']}"
    assert "invoice_number" in res_amazon["missing_fields"], \
        "invoice_number must appear in missing_fields"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 2: Flipkart Invoice — explicit invoice number extracted correctly
    # ----------------------------------------------------------------
    print("Test 2: Flipkart Invoice with Order ID and Invoice Number...")
    flipkart_text = (
        "Flipkart Internet Private Limited\n"
        "Order ID: OD123456789012345600\n"
        "Invoice No: FAB-2024-9988\n"
        "Invoice Date: 2024-09-10\n"
        "Subtotal: Rs. 2400.00\n"
        "Delivery Charges: Rs. 99.50\n"
        "Total Amount: Rs. 2499.50"
    )
    res_flipkart = parser.parse_invoice_pdf(make_pdf(flipkart_text))
    print("  Result:", res_flipkart)
    assert res_flipkart["vendor_name"] == "Flipkart", \
        f"Expected Flipkart, got {res_flipkart['vendor_name']}"
    assert res_flipkart["invoice_number"] == "FAB-2024-9988", \
        f"Expected FAB-2024-9988, got {res_flipkart['invoice_number']}"
    assert res_flipkart["order_number"] == "OD123456789012345600", \
        f"Expected OD..., got {res_flipkart['order_number']}"
    assert res_flipkart["total_amount"] == 2499.5, \
        f"Expected 2499.5, got {res_flipkart['total_amount']}"
    # invoice_date was explicitly present and not in the future
    assert res_flipkart["invoice_date"] == "2024-09-10", \
        f"Expected 2024-09-10, got {res_flipkart['invoice_date']}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 3: Meesho Invoice — order number and date extracted; no invoice number
    # ----------------------------------------------------------------
    print("Test 3: Meesho Invoice with Order No and Amount Due...")
    meesho_text = (
        "Fashnear Technologies Pvt Ltd (Meesho)\n"
        "Order No: 987654321_1\n"
        "Dated: 12/07/2024\n"
        "Price: Rs. 450.00\n"
        "Handling: Rs. 49.00\n"
        "Amount Due: Rs. 499.00"
    )
    res_meesho = parser.parse_invoice_pdf(make_pdf(meesho_text))
    print("  Result:", res_meesho)
    assert res_meesho["vendor_name"] == "Meesho", \
        f"Expected Meesho, got {res_meesho['vendor_name']}"
    # "Order No: ..." goes to order_number; invoice_number stays None
    assert res_meesho["order_number"] == "987654321_1", \
        f"Expected 987654321_1, got {res_meesho['order_number']}"
    assert res_meesho["invoice_number"] is None, \
        f"Expected invoice_number=None, got {res_meesho['invoice_number']}"
    assert res_meesho["total_amount"] == 499.0, \
        f"Expected 499.0, got {res_meesho['total_amount']}"
    # Dated: 12/07/2024 → DD/MM/YYYY → 2024-07-12
    assert res_meesho["invoice_date"] == "2024-07-12", \
        f"Expected 2024-07-12, got {res_meesho['invoice_date']}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 4: Blank PDF (No text layer) → Failed
    # ----------------------------------------------------------------
    print("Test 4: Blank PDF with empty text layer...")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    res_blank = parser.parse_invoice_pdf(buf.getvalue())
    print("  Result:", res_blank)
    assert res_blank["status"] == "Failed", \
        f"Expected Failed, got {res_blank['status']}"
    assert res_blank["total_amount"] is None, \
        f"Expected total_amount=None, got {res_blank['total_amount']}"
    assert res_blank.get("error_message"), "Expected a non-empty error_message"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 5: Random text (no total) → Needs Review (not Failed)
    # ----------------------------------------------------------------
    print("Test 5: PDF with random essay text (pattern matching fails)...")
    res_random = parser.parse_invoice_pdf(make_pdf(
        "This is a random document about nature.\nIt contains trees and flowers."
    ))
    print("  Result:", res_random)
    # Parser returns "Needs Review" (total_amount is None) not "Failed" (PDF was readable)
    assert res_random["status"] == "Needs Review", \
        f"Expected Needs Review (no total found), got {res_random['status']}"
    assert res_random["total_amount"] is None, \
        f"Expected total_amount=None, got {res_random['total_amount']}"
    assert res_random.get("error_message"), "Expected a non-empty error_message"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 6: Corrupt PDF bytes → Failed
    # ----------------------------------------------------------------
    print("Test 6: Corrupt PDF bytes (graceful exception handling)...")
    res_corrupt = parser.parse_invoice_pdf(b"Not a real PDF stream at all!")
    print("  Result:", res_corrupt)
    assert res_corrupt["status"] == "Failed", \
        f"Expected Failed, got {res_corrupt['status']}"
    assert res_corrupt["total_amount"] is None, \
        f"Expected total_amount=None, got {res_corrupt['total_amount']}"
    assert res_corrupt.get("error_message"), "Expected a non-empty error_message"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 7: Currency detection — no symbol → None, not "INR"
    # ----------------------------------------------------------------
    print("Test 7: Currency extraction — no currency signal returns None...")
    no_cur_text = (
        "Vendor Corp\n"
        "Invoice Number: INV-2024-001\n"
        "Invoice Date: 01/01/2024\n"
        "Grand Total: 5000.00"
    )
    res_no_cur = parser.parse_invoice_pdf(make_pdf(no_cur_text))
    print("  Result:", res_no_cur)
    assert res_no_cur["currency"] is None, \
        f"Expected currency=None (no symbol found), got {res_no_cur['currency']}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 8: Explicit INR symbol → "INR" detected
    # ----------------------------------------------------------------
    print("Test 8: Currency extraction — Rs. prefix detected as INR...")
    inr_text = (
        "Vendor Corp\n"
        "Invoice Number: INV-2024-002\n"
        "Invoice Date: 01/01/2024\n"
        "Grand Total: Rs. 5000.00"
    )
    res_inr = parser.parse_invoice_pdf(make_pdf(inr_text))
    print("  Result:", res_inr)
    assert res_inr["currency"] == "INR", \
        f"Expected currency=INR, got {res_inr['currency']}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 9: validate_invoice function
    # ----------------------------------------------------------------
    print("Test 9: validate_invoice — balance mismatch flagged...")
    bad_data = {
        "vendor_name": "ACME Corp",
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "total_amount": 1000.0,
        "currency": "INR",
        "subtotal": 800.0,
        "tax_amount": 100.0,  # 800 + 100 = 900 ≠ 1000
        "shipping_charges": None,
        "discount": None,
        "line_items": None,
        "tax_breakup": None,
    }
    result = parser.validate_invoice(bad_data)
    print("  Result:", result)
    assert not result["valid"], "Expected invalid (balance mismatch)"
    assert len(result["validation_errors"]) > 0, "Expected validation_errors to be non-empty"
    print("  -> PASSED!\n")

    print("Test 10: validate_invoice — all checks pass...")
    good_data = {
        "vendor_name": "ACME Corp",
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "total_amount": 944.0,
        "currency": "INR",
        "subtotal": 800.0,
        "tax_amount": 144.0,  # 18% GST
        "shipping_charges": None,
        "discount": None,
        "line_items": None,
        "tax_breakup": None,
    }
    result_good = parser.validate_invoice(good_data)
    print("  Result:", result_good)
    assert result_good["valid"], f"Expected valid, got errors: {result_good}"
    print("  -> PASSED!\n")

    print("Test 11: validate_invoice — decimal amounts & flexible tolerance (e.g. 1370.04, 208.99)...")
    decimal_data = {
        "vendor_name": "Amazon India",
        "invoice_number": "DED4-12339",
        "invoice_date": "2024-09-23",
        "total_amount": 1370.04,
        "currency": "INR",
        "subtotal": 1161.05,
        "tax_amount": 208.99,
        "shipping_charges": 0.0,
        "discount": 0.0,
        "line_items": [
            {"description": "Amazon India Service", "quantity": 1, "unit_price": 1161.05, "line_total": 1161.05},
            {"description": "GST 18%", "quantity": 1, "unit_price": 208.99, "line_total": 208.99},
        ],
        "tax_breakup": None,
    }
    res_dec = parser.validate_invoice(decimal_data)
    print("  Result:", res_dec)
    assert res_dec["valid"], f"Expected decimal invoice valid, got: {res_dec}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 12: Explicit Total Tax Matching (Req 1)
    # ----------------------------------------------------------------
    print("Test 12: Explicit Total Tax Matching across various summary labels...")
    explicit_tax_cases = [
        ("Total Tax: 128.50", 128.50),
        ("Total Tax: ₹128.50", 128.50),
        ("Total Tax: INR 128.50", 128.50),
        ("Total Tax: Rs. 128.50", 128.50),
        ("Total GST: 128.50", 128.50),
        ("Total GST: ₹128.50", 128.50),
        ("GST Amount: 128.50", 128.50),
        ("GST Amount: ₹ 128.50", 128.50),
        ("Integrated Tax: 128.50", 128.50),
        ("Integrated Tax: ₹128.50", 128.50),
        ("Central Tax + State Tax: 128.50", 128.50),
        ("Central Tax & State Tax: ₹128.50", 128.50),
        ("Central Tax and State Tax: INR 128.50", 128.50),
        ("Tax Amount: 128.50", 128.50),
        ("Tax Amount: ₹128.50", 128.50),
        ("Total Tax Amount: 128.50", 128.50),
        ("Total Tax Amount: ₹128.50", 128.50),
        ("Total Tax Amount: INR 128.50", 128.50),
    ]
    for text, expected in explicit_tax_cases:
        amt = parser.extract_tax_amount(text)
        assert amt == expected, f"Failed for {text!r}: expected {expected}, got {amt}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 13: CGST / SGST / IGST Breakup & Fallback Sum (Req 2)
    # ----------------------------------------------------------------
    print("Test 13: CGST / SGST / UTGST / IGST breakup & fallback sum...")
    b1 = parser.extract_tax_breakup("CGST @ 9%: 45.82\nSGST @ 9%: 45.82")
    assert b1 == {"CGST_9": 45.82, "SGST_9": 45.82}, f"Breakup failed: {b1}"
    assert parser.extract_tax_amount("CGST @ 9%: 45.82\nSGST @ 9%: 45.82") == 91.64

    b2 = parser.extract_tax_breakup("Integrated Tax @ 18%: 128.50")
    assert b2 == {"IGST_18": 128.50}, f"Breakup failed: {b2}"
    assert parser.extract_tax_amount("Integrated Tax @ 18%: 128.50") == 128.50

    b3 = parser.extract_tax_breakup("UTGST @ 9%: 45.82\nCGST @ 9%: 45.82")
    assert b3 == {"UTGST_9": 45.82, "CGST_9": 45.82}, f"Breakup failed: {b3}"
    assert parser.extract_tax_amount("UTGST @ 9%: 45.82\nCGST @ 9%: 45.82") == 91.64

    b4 = parser.extract_tax_breakup("Central Tax 9%: 45.82\nState Tax 9%: 45.82")
    assert b4 == {"CGST_9": 45.82, "SGST_9": 45.82}, f"Breakup failed: {b4}"
    assert parser.extract_tax_amount("Central Tax 9%: 45.82\nState Tax 9%: 45.82") == 91.64

    # Single "Total Tax" summary line present alongside component breakup:
    # Explicit summary must be preferred without double-counting
    summary_with_components = (
        "CGST @ 9%: 45.82\n"
        "SGST @ 9%: 45.82\n"
        "Total Tax: 91.64"
    )
    assert parser.extract_tax_amount(summary_with_components) == 91.64
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 14: Ignore Table Noise & Serial Numbers (Req 3)
    # ----------------------------------------------------------------
    print("Test 14: Ignore table noise, serial numbers, HSN/SAC codes, rates...")
    noise_case1 = "Sl No: 1 | HSN/SAC: 84713010 | Item: Laptop | Qty: 2 | Total Tax Amount: ₹128.50"
    assert parser.extract_tax_amount(noise_case1) == 128.50

    noise_case2 = "Total Tax @ 18%: 128.50"
    assert parser.extract_tax_amount(noise_case2) == 128.50

    noise_case3 = "1 8471 USB Cable 2 500.00 CGST 9% 45.82 SGST 9% 45.82 1091.64"
    assert parser.extract_tax_amount(noise_case3) == 91.64

    noise_case4 = "Total Taxable Value: 1000.00\nTotal Tax: 180.00"
    assert parser.extract_tax_amount(noise_case4) == 180.00

    noise_case5 = "Tax Invoice No: 99881\nTax Rate: 18%\nTax Amount: 180.00"
    assert parser.extract_tax_amount(noise_case5) == 180.00

    noise_case6 = "Total Tax: 1 128.50"
    assert parser.extract_tax_amount(noise_case6) == 128.50
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 15: Preserve Decimals & Formatting (Req 4)
    # ----------------------------------------------------------------
    print("Test 15: Preserve exact decimals without rounding off fractions...")
    dec_cases = [
        ("Total Tax: 45.82", 45.82),
        ("CGST @ 9%: 22.91\nSGST @ 9%: 22.91", 45.82),
        ("Total Tax Amount: 208.99", 208.99),
        ("Total Tax: 0.50", 0.50),
    ]
    for text, expected in dec_cases:
        res = parser.extract_tax_amount(text)
        assert res == expected, f"Expected {expected}, got {res}"
    print("  -> PASSED!\n")

    # ----------------------------------------------------------------
    # Test 16: End-to-end PDF parsing with Tax Extraction
    # ----------------------------------------------------------------
    print("Test 16: End-to-end PDF invoice parsing with tax extraction and validation...")
    pdf_with_tax = (
        "ACME Corp India Private Limited\n"
        "Invoice Number: INV-2024-8888\n"
        "Invoice Date: 2024-05-15\n"
        "Subtotal: Rs. 1000.00\n"
        "CGST @ 9%: 45.82\n"
        "SGST @ 9%: 45.82\n"
        "Total Tax Amount: Rs. 91.64\n"
        "Grand Total: Rs. 1091.64"
    )
    res_pdf = parser.parse_invoice_pdf(make_pdf(pdf_with_tax))
    assert res_pdf["tax_amount"] == 91.64, f"Expected 91.64, got {res_pdf['tax_amount']}"
    assert res_pdf["tax_breakup"] == {"CGST_9": 45.82, "SGST_9": 45.82}
    assert res_pdf["total_amount"] == 1091.64
    assert res_pdf["status"] == "Extracted"
    assert res_pdf["validation_errors"] == []
    print("  -> PASSED!\n")

    print("ALL TESTS PASSED SUCCESSFULLY! :)")


if __name__ == "__main__":
    run_tests()
