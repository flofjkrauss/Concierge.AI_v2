"""session manager for interactive chat sessions"""

from configuration.application import ApplicationSettings
from conversation.data_collector import DataCollector
from conversation.entities.information import Information
from conversation.entities.session import Session
from conversation.value_object.intent import Intent
from observability.log_messages import LOG_MSG


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self.settings = ApplicationSettings.get_settings()

    def start_session(self) -> Session:
        collector = DataCollector()
        session = Session(collector=collector)
        self._sessions[session.session_id] = session
        LOG_MSG.debug(f"New conversation session started: {session.session_id}")
        return session

    def get_session(self, session_id: str) -> Session | None:
        """retrieve session by session_id"""
        if session_id in self._sessions:
            return self._sessions[session_id]
        else:
            return None

    def terminate_session(self, session: Session) -> None:
        self._sessions.pop(session.session_id, None)
        LOG_MSG.debug(f"Session {session.session_id} terminated.")

    def unknown_intent_threshold_exeeded(self, session: Session, intent: Intent, informations: list[Information]) -> bool:
        if all([
            intent == Intent.UNKNOWN,            
            len(informations) == 0
        ]):
            session.increase_unknown_counter()
            if session.unknown_counter > self.settings.max_num_msg_with_intent_unknown:
                LOG_MSG.debug(f"Session {session.session_id} exeeded the unknown intent message threshold.")
                return True

        return False
