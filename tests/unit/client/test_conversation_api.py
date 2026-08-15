from unittest.mock import Mock

import httpx
import pytest

from client.components.api import (
    ConversationApi,
    ConversationApiError,
    ConversationResponse,
    ResponseKind,
)


def test_response_kind_uses_structured_fields() -> None:
    greeting = ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Welcome",
            "session_id": "session-1",
        }
    )
    availability = ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Options",
            "content": {"rooms": []},
        }
    )
    confirmation = ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Localized text that does not identify the action",
            "data": {"booking_id": "booking-1"},
        }
    )

    assert greeting.kind is ResponseKind.GREETING
    assert greeting.session_id == "session-1"
    assert availability.kind is ResponseKind.AVAILABILITY
    assert confirmation.kind is ResponseKind.CONFIRMATION


def test_response_accessors_filter_unusable_structured_values() -> None:
    response = ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Options",
            "content": {
                "rooms": [{"category": "double"}, "invalid"],
                "request": {"guest_count": 2},
            },
            "data": {"booking_id": "booking-1"},
        }
    )

    assert response.rooms() == [{"category": "double"}]
    assert response.availability_request() == {"guest_count": 2}
    assert response.structured_data("data") == {"booking_id": "booking-1"}
    assert response.structured_data("missing") is None


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        ({"session_active": True, "text": "Error", "reason": "bad"}, ResponseKind.ERROR),
        ({"session_active": True, "text": "Booking", "content": {}}, ResponseKind.BOOKING),
        ({"session_active": True, "text": "Message"}, ResponseKind.MESSAGE),
    ],
)
def test_response_kind_covers_remaining_contract_shapes(
    payload: dict[str, object],
    kind: ResponseKind,
) -> None:
    assert ConversationResponse.from_payload(payload).kind is kind


def test_invalid_response_contract_is_rejected() -> None:
    with pytest.raises(ConversationApiError, match="Invalid conversation response"):
        ConversationResponse.from_payload({"text": "Missing state"})


def test_api_url_is_restricted_to_conversation_prefix() -> None:
    with pytest.raises(ValueError, match="/api/conversation"):
        ConversationApi("http://127.0.0.1:8000/api/bookings")


def test_send_message_uses_encoded_path_and_query_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_post(
        url: str,
        *,
        params: dict[str, str] | None,
        timeout: float,
    ) -> httpx.Response:
        captured.update(url=url, params=params, timeout=timeout)
        request = httpx.Request("POST", url, params=params)
        return httpx.Response(
            200,
            request=request,
            json={"session_active": True, "text": "Received"},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    response = ConversationApi(
        "http://127.0.0.1:8000/api/conversation",
        turn_timeout_seconds=30.0,
    ).send_message("session/one", "Family room & breakfast")

    assert captured == {
        "url": "http://127.0.0.1:8000/api/conversation/session%2Fone",
        "params": {"message": "Family room & breakfast"},
        "timeout": 30.0,
    }
    assert response.kind is ResponseKind.MESSAGE


def test_terminate_posts_to_conversation_scoped_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post = Mock(
        return_value=httpx.Response(
            204,
            request=httpx.Request(
                "POST",
                "http://127.0.0.1:8000/api/conversation/session-1/terminate",
            ),
        )
    )
    monkeypatch.setattr(httpx, "post", post)
    api = ConversationApi("http://127.0.0.1:8000/api/conversation")

    api.terminate("session-1")

    post.assert_called_once_with(
        "http://127.0.0.1:8000/api/conversation/session-1/terminate",
        params=None,
        timeout=30.0,
    )


def test_initialize_and_patience_use_their_scoped_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post = Mock(
        side_effect=[
            httpx.Response(
                200,
                request=httpx.Request("POST", "http://hotel/api/conversation/"),
                json={
                    "session_active": True,
                    "text": "Welcome",
                    "session_id": "session-1",
                },
            ),
            httpx.Response(
                200,
                request=httpx.Request(
                    "POST",
                    "http://hotel/api/conversation/session-1/patience",
                ),
                json={"session_active": True, "text": "Still working"},
            ),
        ]
    )
    monkeypatch.setattr(httpx, "post", post)
    api = ConversationApi("http://hotel/api/conversation")

    assert api.initialize().session_id == "session-1"
    assert api.patience_message("session-1", "book").text == "Still working"
    assert post.call_args_list[0].args[0].endswith("/api/conversation/")
    assert post.call_args_list[1].kwargs["params"] == {"message": "book"}


def test_transport_and_non_mapping_payload_errors_are_guest_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        Mock(side_effect=httpx.ConnectError("offline")),
    )
    api = ConversationApi("http://hotel/api/conversation")

    with pytest.raises(ConversationApiError, match="request failed"):
        api.initialize()

    response = httpx.Response(
        200,
        request=httpx.Request("POST", "http://hotel/api/conversation/"),
        json=["not", "a", "mapping"],
    )
    monkeypatch.setattr(httpx, "post", Mock(return_value=response))
    with pytest.raises(ConversationApiError, match="Invalid conversation response"):
        api.initialize()
