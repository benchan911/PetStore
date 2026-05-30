import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def auth_header(user_id="owner-id", role="owner"):
    return {"Authorization": f"Bearer {user_id}:{role}"}


@patch("app.supabase")
def test_create_booking(mock_supabase, client):
    pet_result = MagicMock()
    pet_result.data = [{"id": "pet-id"}]
    booking_result = MagicMock()
    booking_result.data = [{"id": "booking-id", "status": "open"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = pet_result
    mock_supabase.table.return_value.insert.return_value.execute.return_value = booking_result

    response = client.post(
        "/bookings",
        json={
            "pet_id": "pet-id",
            "start_date": "2024-06-01",
            "end_date": "2024-06-03",
            "description": "Walk my dog",
            "budget": 150,
        },
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 201


@patch("app.supabase")
def test_create_booking_missing_fields(mock_supabase, client):
    response = client.post(
        "/bookings",
        json={"pet_id": "pet-id"},
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 400


@patch("app.supabase")
def test_get_bookings_owner(mock_supabase, client):
    mock_result = MagicMock()
    mock_result.data = [{"id": "booking-id", "status": "open"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    response = client.get("/bookings", headers=auth_header("owner-id", "owner"))

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


@patch("app.supabase")
def test_get_bookings_caretaker(mock_supabase, client):
    mock_result = MagicMock()
    mock_result.data = [{"id": "booking-id", "status": "open"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    response = client.get("/bookings", headers=auth_header("caretaker-id", "caretaker"))

    assert response.status_code == 200


@patch("app.supabase")
def test_apply_to_booking(mock_supabase, client):
    status_result = MagicMock()
    status_result.data = [{"status": "open"}]
    app_result = MagicMock()
    app_result.data = [{"id": "app-id", "caretaker_id": "caretaker-id"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = status_result
    mock_supabase.table.return_value.insert.return_value.execute.return_value = app_result

    response = client.post(
        "/bookings/booking-id/apply",
        json={"message": "I can help!", "proposed_rate": 25.0},
        headers=auth_header("caretaker-id", "caretaker"),
    )

    assert response.status_code == 201


@patch("app.supabase")
def test_apply_to_closed_booking(mock_supabase, client):
    mock_result = MagicMock()
    mock_result.data = [{"status": "confirmed"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    response = client.post(
        "/bookings/booking-id/apply",
        json={"message": "I can help!"},
        headers=auth_header("caretaker-id", "caretaker"),
    )

    assert response.status_code == 400


@patch("app.send_applicant_confirmed_email")
@patch("app.send_applicant_rejected_email")
@patch("app.supabase")
def test_confirm_applicant(mock_supabase, mock_rejected, mock_confirmed, client):
    booking_result = MagicMock()
    booking_result.data = [{
        "id": "booking-id",
        "pets": {"name": "Buddy"},
        "start_date": "2024-06-01",
        "end_date": "2024-06-03",
        "description": "Walk",
    }]
    apps_result = MagicMock()
    apps_result.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = booking_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = apps_result

    response = client.post(
        "/bookings/booking-id/confirm",
        json={"application_id": "app-id"},
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 200


# --- Cancel booking tests ---

@patch("app.supabase")
def test_cancel_booking(mock_supabase, client):
    booking_result = MagicMock()
    booking_result.data = [{"owner_id": "owner-id", "status": "open"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = booking_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    response = client.delete(
        "/bookings/booking-id",
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Booking cancelled successfully"


@patch("app.supabase")
def test_cancel_confirmed_booking(mock_supabase, client):
    booking_result = MagicMock()
    booking_result.data = [{"owner_id": "owner-id", "status": "confirmed"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = booking_result

    response = client.delete(
        "/bookings/booking-id",
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 400
    assert "confirmed" in response.get_json()["error"]


@patch("app.supabase")
def test_cancel_booking_not_owner(mock_supabase, client):
    booking_result = MagicMock()
    booking_result.data = [{"owner_id": "other-owner-id", "status": "open"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = booking_result

    response = client.delete(
        "/bookings/booking-id",
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 404


# --- Withdraw application tests ---

@patch("app.supabase")
def test_withdraw_application(mock_supabase, client):
    app_result = MagicMock()
    app_result.data = [{"caretaker_id": "caretaker-id", "status": "pending"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = app_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    response = client.delete(
        "/bookings/booking-id/applications/app-id",
        headers=auth_header("caretaker-id", "caretaker"),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Application withdrawn successfully"


@patch("app.supabase")
def test_withdraw_application_not_owner(mock_supabase, client):
    app_result = MagicMock()
    app_result.data = [{"caretaker_id": "other-caretaker-id", "status": "pending"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = app_result

    response = client.delete(
        "/bookings/booking-id/applications/app-id",
        headers=auth_header("caretaker-id", "caretaker"),
    )

    assert response.status_code == 404


@patch("app.supabase")
def test_withdraw_non_pending_application(mock_supabase, client):
    app_result = MagicMock()
    app_result.data = [{"caretaker_id": "caretaker-id", "status": "accepted"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = app_result

    response = client.delete(
        "/bookings/booking-id/applications/app-id",
        headers=auth_header("caretaker-id", "caretaker"),
    )

    assert response.status_code == 400
    assert "accepted" in response.get_json()["error"]


# --- Reject application tests ---

@patch("app.supabase")
def test_reject_application(mock_supabase, client):
    booking_result = MagicMock()
    booking_result.data = [{"owner_id": "owner-id", "status": "open"}]
    app_result = MagicMock()
    app_result.data = [{"status": "pending"}]
    # Booking query: .select().eq().execute()  (single eq)
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = booking_result
    # Application query: .select().eq().eq().execute()  (double eq)
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = app_result
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    response = client.post(
        "/bookings/booking-id/applications/app-id/reject",
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Application rejected successfully"


@patch("app.supabase")
def test_reject_application_not_owner(mock_supabase, client):
    booking_result = MagicMock()
    booking_result.data = [{"owner_id": "other-owner-id", "status": "open"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = booking_result

    response = client.post(
        "/bookings/booking-id/applications/app-id/reject",
        headers=auth_header("owner-id", "owner"),
    )

    assert response.status_code == 404


def test_reject_application_wrong_role(client):
    response = client.post(
        "/bookings/booking-id/applications/app-id/reject",
        headers=auth_header("caretaker-id", "caretaker"),
    )

    assert response.status_code == 403
