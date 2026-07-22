"""API dependencies."""

from app.database.session import get_db
from app.services.chat_service import ChatService
from app.services.dashboard_service import DashboardService
from app.services.email_service import EmailService
from app.services.knowledge_service import KnowledgeService
from app.services.log_service import LogService
from app.services.prompt_service import PromptService
from app.services.settings_service import SettingsService
from app.services.style_service import StyleService
from app.services.workspace_service import WorkspaceService

__all__ = ["get_db", "get_services"]


class Services:
    def __init__(self):
        self._email: EmailService | None = None
        self._knowledge: KnowledgeService | None = None
        self._workspace: WorkspaceService | None = None
        self._prompt: PromptService | None = None
        self._settings: SettingsService | None = None
        self._style: StyleService | None = None
        self._log: LogService | None = None
        self._chat: ChatService | None = None
        self._dashboard: DashboardService | None = None

    @property
    def email(self) -> EmailService:
        if self._email is None:
            self._email = EmailService()
        return self._email

    @property
    def knowledge(self) -> KnowledgeService:
        if self._knowledge is None:
            self._knowledge = KnowledgeService()
        return self._knowledge

    @property
    def workspace(self) -> WorkspaceService:
        if self._workspace is None:
            self._workspace = WorkspaceService()
        return self._workspace

    @property
    def prompt(self) -> PromptService:
        if self._prompt is None:
            self._prompt = PromptService()
        return self._prompt

    @property
    def settings(self) -> SettingsService:
        if self._settings is None:
            self._settings = SettingsService()
        return self._settings

    @property
    def style(self) -> StyleService:
        if self._style is None:
            self._style = StyleService()
        return self._style

    @property
    def log(self) -> LogService:
        if self._log is None:
            self._log = LogService()
        return self._log

    @property
    def chat(self) -> ChatService:
        if self._chat is None:
            self._chat = ChatService()
        return self._chat

    @property
    def dashboard(self) -> DashboardService:
        if self._dashboard is None:
            self._dashboard = DashboardService()
        return self._dashboard


_services: Services | None = None


def get_services() -> Services:
    global _services
    if _services is None:
        _services = Services()
    return _services
