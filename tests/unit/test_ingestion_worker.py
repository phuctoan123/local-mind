from app.ingestion.worker import IngestionError, safe_ingestion_error


def test_safe_ingestion_error_preserves_expected_user_facing_errors():
    error = IngestionError("No text could be extracted from this document.")

    assert safe_ingestion_error(error) == "No text could be extracted from this document."


def test_safe_ingestion_error_removes_windows_paths():
    error = RuntimeError(
        "failed reading C:\\Users\\Toan\\Documents\\LocalMind\\data\\raw\\secret.pdf"
    )

    message = safe_ingestion_error(error)

    assert "C:\\Users\\Toan" not in message
    assert "secret.pdf" in message


def test_safe_ingestion_error_removes_posix_paths_and_truncates():
    error = RuntimeError(f"failed reading /home/user/localmind/data/raw/secret.pdf {'x' * 500}")

    message = safe_ingestion_error(error)

    assert "/home/user" not in message
    assert "secret.pdf" in message
    assert len(message) == 300
