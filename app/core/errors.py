class WorkspaceError(Exception):
    """Base error intentionally safe to show to a user."""

    user_message = "Не удалось выполнить операцию. Попробуйте ещё раз."


class UnsupportedFileError(WorkspaceError):
    user_message = "Этот формат файла не поддерживается."


class FileTooLargeError(WorkspaceError):
    user_message = "Файл превышает разрешённый размер."


class EmptyFileError(WorkspaceError):
    user_message = "Пустой файл нельзя проанализировать."


class FileReadError(WorkspaceError):
    user_message = "Файл не удалось безопасно прочитать."


class InvalidMimeError(WorkspaceError):
    user_message = "Содержимое файла не соответствует заявленному формату."


class AnalysisError(WorkspaceError):
    user_message = "Не удалось проанализировать данные."


class ChartGenerationError(WorkspaceError):
    user_message = "Для этого графика недостаточно совместимых данных."


class ReportGenerationError(WorkspaceError):
    user_message = "Не удалось сформировать отчёт."


class AIServiceConfigurationError(WorkspaceError):
    user_message = "AI-сервис временно недоступен."


class AIServiceRequestError(WorkspaceError):
    user_message = "AI-анализ временно недоступен, но файл сохранён."


class ArtifactNotFoundError(WorkspaceError):
    user_message = "Артефакт не найден в текущем workspace."


class PolicyDeniedError(WorkspaceError):
    user_message = "Запрошенное действие запрещено политикой безопасности."
