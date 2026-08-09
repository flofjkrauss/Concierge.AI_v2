from configuration.application import ApplicationSettings
from conversation.entities.information import Information
from conversation.session_manager import SessionManager
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


def test_session_manager_starts_retrieves_and_terminates_session() -> None:
    manager = SessionManager()

    session = manager.start_session()

    assert manager.get_session(session.session_id) is session
    manager.terminate_session(session)
    assert manager.get_session(session.session_id) is None


def test_unknown_threshold_is_exceeded_after_configured_limit() -> None:
    manager = SessionManager()
    manager.settings = ApplicationSettings(max_num_msg_with_intent_unknown=1)
    session = manager.start_session()

    assert not manager.unknown_intent_threshold_exeeded(
        session,
        Intent.UNKNOWN,
        [],
    )
    assert manager.unknown_intent_threshold_exeeded(session, Intent.UNKNOWN, [])


def test_unknown_threshold_does_not_increment_when_information_was_found() -> None:
    manager = SessionManager()
    session = manager.start_session()
    information = Information(InformationField.FIRST_NAME, "Alex")

    assert not manager.unknown_intent_threshold_exeeded(
        session,
        Intent.UNKNOWN,
        [information],
    )
    assert session.unknown_counter == 0
