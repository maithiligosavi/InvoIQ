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
    all_passed = True

    # Test 1: Amazon Invoice
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
    assert res_amazon["status"] == "Processed", f"Expected Processed, got {res_amazon['status']}"
    assert res_amazon["vendor_name"] == "Amazon India", f"Expected Amazon India, got {res_amazon['vendor_name']}"
    assert res_amazon["invoice_number"] == "408-1234567-1234567", f"Expected 408-1234567-1234567, got {res_amazon['invoice_number']}"
    assert res_amazon["total_amount"] == 1538.0, f"Expected 1538.0, got {res_amazon['total_amount']}"
    print("  -> PASSED!\n")

    # Test 2: Flipkart Invoice
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
    assert res_flipkart["status"] == "Processed"
    assert res_flipkart["vendor_name"] == "Flipkart"
    assert res_flipkart["invoice_number"] == "FAB-2024-9988"
    assert res_flipkart["total_amount"] == 2499.5
    print("  -> PASSED!\n")

    # Test 3: Meesho Invoice
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
    assert res_meesho["status"] == "Processed"
    assert res_meesho["vendor_name"] == "Meesho"
    assert res_meesho["invoice_number"] == "987654321_1"
    assert res_meesho["total_amount"] == 499.0
    print("  -> PASSED!\n")

    # Test 4: Blank PDF (No text layer)
    print("Test 4: Blank PDF with empty text layer...")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    res_blank = parser.parse_invoice_pdf(buf.getvalue())
    print("  Result:", res_blank)
    assert res_blank["status"] == "Failed"
    assert res_blank["total_amount"] == 0.0
    assert "error_message" in res_blank and res_blank["error_message"]
    print("  -> PASSED!\n")

    # Test 5: Pattern Matching Failure (Random text without total)
    print("Test 5: PDF with random essay text (pattern matching fails)...")
    res_random = parser.parse_invoice_pdf(make_pdf("This is a random document about nature.\nIt contains trees and flowers."))
    print("  Result:", res_random)
    assert res_random["status"] == "Failed"
    assert res_random["total_amount"] == 0.0
    assert "error_message" in res_random and res_random["error_message"]
    print("  -> PASSED!\n")

    # Test 6: Corrupt PDF bytes
    print("Test 6: Corrupt PDF bytes (graceful exception handling)...")
    res_corrupt = parser.parse_invoice_pdf(b"Not a real PDF stream at all!")
    print("  Result:", res_corrupt)
    assert res_corrupt["status"] == "Failed"
    assert res_corrupt["total_amount"] == 0.0
    assert "error_message" in res_corrupt and res_corrupt["error_message"]
    print("  -> PASSED!\n")

    print("ALL TESTS PASSED SUCCESSFULLY! :)")


if __name__ == "__main__":
    run_tests()
