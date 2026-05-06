import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../shared"))


def _mock_verify_jwt(token):
    """Decode token as 'user_id:role' for testing."""
    if ":" in token:
        user_id, role = token.split(":", 1)
    else:
        user_id, role = token, "owner"
    return {"id": user_id, "user_metadata": {"role": role}}


@pytest.fixture(autouse=True)
def bypass_jwt(monkeypatch):
    import jwt_middleware
    monkeypatch.setattr(jwt_middleware, "verify_jwt", _mock_verify_jwt)
