import io
import csv
from fastapi.testclient import TestClient
from main import app
from auth.mock_provider import MockAuthProvider

client = TestClient(app)
_provider = MockAuthProvider(users="testuser", secret="local-dev-secret-change-me")


def _auth_header():
    token = _provider.login("testuser")
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_auth():
    response = client.post("/api/files/upload", files={"file": ("test.csv", b"data", "text/csv")})
    assert response.status_code == 401


def test_upload_rejects_disallowed_type():
    response = client.post(
        "/api/files/upload",
        files={"file": ("malware.exe", b"bad", "application/octet-stream")},
        headers=_auth_header(),
    )
    assert response.status_code == 400
    assert "file_type_not_allowed" in str(response.json())


def test_upload_blocks_ni_in_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "NI"])
    writer.writerow(["John", "AB123456C"])
    csv_bytes = output.getvalue().encode()

    response = client.post(
        "/api/files/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "uk_national_insurance"


def test_upload_clean_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Client", "Revenue"])
    writer.writerow(["Acme", "50000"])
    csv_bytes = output.getvalue().encode()

    response = client.post(
        "/api/files/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "data.csv"
    assert "Acme" in response.json()["file_content"]


# --- Regression tests: file upload edge cases ---

def test_upload_blocks_card_number_in_csv():
    """Credit card numbers in CSV content should be blocked."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Client", "Payment Method"])
    writer.writerow(["Acme", "4111111111111111"])
    csv_bytes = output.getvalue().encode()

    response = client.post(
        "/api/files/upload",
        files={"file": ("payments.csv", csv_bytes, "text/csv")},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "credit_card"


def test_upload_txt_file_scanned():
    """Plain text files should be scanned for sensitive data."""
    content = b"Employee record: NI number AB123456C"
    response = client.post(
        "/api/files/upload",
        files={"file": ("notes.txt", content, "text/plain")},
        headers=_auth_header(),
    )
    assert response.status_code == 403


def test_upload_clean_txt_file():
    """Clean text file should upload successfully."""
    content = b"Q3 revenue summary: total 2.5M GBP"
    response = client.post(
        "/api/files/upload",
        files={"file": ("summary.txt", content, "text/plain")},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "summary.txt"


def test_upload_response_includes_file_content():
    """Successful upload should return extracted text content."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Quarter", "Revenue"])
    writer.writerow(["Q1", "1200000"])
    writer.writerow(["Q2", "1350000"])
    csv_bytes = output.getvalue().encode()

    response = client.post(
        "/api/files/upload",
        files={"file": ("revenue.csv", csv_bytes, "text/csv")},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    data = response.json()
    assert "1200000" in data["file_content"]
    assert data["size"] > 0


def test_upload_multiple_disallowed_extensions():
    """Various disallowed file types should all be rejected."""
    for ext, mime in [(".py", "text/plain"), (".js", "text/javascript"), (".zip", "application/zip")]:
        response = client.post(
            "/api/files/upload",
            files={"file": (f"file{ext}", b"content", mime)},
            headers=_auth_header(),
        )
        assert response.status_code == 400, f"Expected 400 for {ext}, got {response.status_code}"
