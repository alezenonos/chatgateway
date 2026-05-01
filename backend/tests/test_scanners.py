import io
import csv
from filter.scanners import extract_text_from_csv, extract_text_from_xlsx


def test_extract_text_from_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "NI Number", "Amount"])
    writer.writerow(["John Doe", "AB123456C", "5000"])
    content = output.getvalue().encode()
    text = extract_text_from_csv(content)
    assert "AB123456C" in text
    assert "John Doe" in text


def test_extract_text_from_xlsx(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Client", "Account"])
    ws.append(["Acme Corp", "12-34-56 12345678"])
    path = tmp_path / "test.xlsx"
    wb.save(path)
    with open(path, "rb") as f:
        content = f.read()
    text = extract_text_from_xlsx(content)
    assert "12-34-56 12345678" in text
    assert "Acme Corp" in text
