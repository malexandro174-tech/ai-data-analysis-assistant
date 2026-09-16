from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.errors import AIServiceRequestError, ArtifactNotFoundError, WorkspaceError
from app.core.schemas import DatasetSummary

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _services(request: Request): return request.app.state.services


def _conversation(request: Request):
    services = _services(request)
    raw_id = request.cookies.get("workspace_conversation")
    try:
        conversation = services.workspace.get(UUID(raw_id)) if raw_id else services.workspace.create()
    except (ValueError, TypeError):
        conversation = services.workspace.create()
    return conversation


def _response(request: Request, conversation, notice: str = "", error: str = "") -> HTMLResponse:
    services = _services(request)
    active = None
    if conversation.active_file_id:
        try: active = services.files.get(conversation.active_file_id, conversation.conversation_id)
        except WorkspaceError: pass
    response = templates.TemplateResponse(request, "workspace.html", {
        "conversation": conversation, "files": services.files.list_for_session(conversation.conversation_id),
        "artifacts": services.artifacts.list_for_session(conversation.conversation_id), "active": active,
        "notice": notice, "error": error, "resolved_model": services.ai.resolved_model,
        "root_path": request.scope.get("root_path", ""),
    })
    response.set_cookie("workspace_conversation", str(conversation.conversation_id), httponly=True, samesite="lax", secure=services.settings.cookie_secure)
    return response


@router.get("/", response_class=HTMLResponse)
async def page(request: Request):
    return _response(request, _conversation(request))


@router.post("/new-chat")
async def new_chat(request: Request):
    conversation = _services(request).workspace.create()
    response = RedirectResponse(f"{request.scope.get('root_path', '')}/", status_code=303)
    response.set_cookie("workspace_conversation", str(conversation.conversation_id), httponly=True, samesite="lax", secure=_services(request).settings.cookie_secure)
    return response


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    services = _services(request); conversation = _conversation(request)
    try:
        record = await services.files.save_upload(file, conversation.conversation_id)
        conversation.active_file_id = record.file_id; services.workspace.update(conversation); services.workspace.increment("uploads")
        return _response(request, conversation, notice=f"Файл «{record.original_name}» сохранён.")
    except WorkspaceError as exc:
        services.workspace.increment("uploads_rejected"); services.workspace.increment("file_errors")
        return _response(request, conversation, error=exc.user_message)


async def _summary_for_active(request: Request, conversation) -> tuple[object, DatasetSummary | None]:
    services = _services(request)
    if not conversation.active_file_id: return None, None
    record = services.files.get(conversation.active_file_id, conversation.conversation_id)
    if record.kind == "image": return record, None
    frame = await asyncio.to_thread(services.analysis.read, services.files.path_for(record), record.extension)
    return record, await asyncio.to_thread(services.analysis.summarize, frame)


@router.post("/chat")
async def chat(request: Request, question: str = Form(...)):
    services = _services(request); conversation = _conversation(request); question = question.strip()[:1200]
    if not question: return _response(request, conversation, error="Введите запрос для аналитика.")
    services.workspace.append_message(conversation, "user", question)
    try:
        record, summary = await _summary_for_active(request, conversation)
        if record and record.kind == "image":
            services.workspace.increment("vision_requests")
            answer = await services.ai.vision(services.files.path_for(record), record.content_type, question)
            services.workspace.append_message(conversation, "assistant", answer)
            return _response(request, conversation, notice="Multimodal-анализ выполнен.")
        plan = await services.ai.plan(question, summary)
        services.workspace.append_message(conversation, "assistant", plan.assistant_message)
        notices = [plan.assistant_message]
        frame = await asyncio.to_thread(services.analysis.read, services.files.path_for(record), record.extension) if record and summary else None
        for action in plan.actions:
            if action.type == "analyze" and summary:
                services.workspace.increment("analysis_requests"); notices.append(services.analysis.concise_findings(summary))
            elif action.type == "preview" and summary:
                notices.append(f"Preview готов: {len(summary.preview)} строк для безопасного просмотра.")
            elif action.type == "generate_chart" and frame is not None:
                chart = await asyncio.to_thread(services.charts.generate, frame, services.settings.outputs_dir, conversation.conversation_id, action.chart_type or "bar", action.x_column, action.y_column)
                artifact = services.artifacts.register(conversation.conversation_id, record.file_id, "chart_png", chart.name, chart, {"chart_type": action.chart_type or "bar", "source_name": record.original_name})
                conversation.artifact_ids.append(artifact.artifact_id); services.workspace.update(conversation); services.workspace.increment("charts_generated"); notices.append("График добавлен в артефакты.")
            elif action.type == "generate_report" and summary:
                report = await asyncio.to_thread(services.reports.generate, services.settings.outputs_dir, conversation.conversation_id, record.original_name, summary, services.analysis.concise_findings(summary), None)
                artifact = services.artifacts.register(conversation.conversation_id, record.file_id, "report_docx", report.name, report)
                conversation.artifact_ids.append(artifact.artifact_id); services.workspace.update(conversation); services.workspace.increment("reports_generated"); notices.append("DOCX-отчёт добавлен в артефакты.")
            elif action.type == "save_summary" and summary:
                await _save_summary(request, conversation, record.file_id, record.original_name, summary)
                notices.append("Markdown summary добавлен в артефакты.")
        return _response(request, conversation, notice=" ".join(notices))
    except AIServiceRequestError as exc:
        services.workspace.increment("provider_errors"); services.workspace.append_message(conversation, "assistant", exc.user_message)
        return _response(request, conversation, error=exc.user_message)
    except WorkspaceError as exc:
        services.workspace.increment("file_errors"); return _response(request, conversation, error=exc.user_message)


async def _save_summary(request: Request, conversation, source_id, file_name: str, summary: DatasetSummary):
    services = _services(request); directory = services.settings.outputs_dir / str(conversation.conversation_id); directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"summary-{conversation.conversation_id}.md"
    content = f"# Data summary\n\n- File: {file_name}\n- Rows: {summary.row_count}\n- Columns: {summary.column_count}\n\n## Key observations\n\n" + "\n".join(f"- {item['name']}: {item['classification']}, missing {item['missing']}" for item in summary.columns) + "\n"
    await asyncio.to_thread(target.write_text, content, "utf-8")
    artifact = services.artifacts.register(conversation.conversation_id, source_id, "summary_md", target.name, target)
    conversation.artifact_ids.append(artifact.artifact_id); services.workspace.update(conversation); services.workspace.increment("summaries_saved")


@router.post("/chart/{chart_type}")
async def chart(request: Request, chart_type: str):
    services = _services(request); conversation = _conversation(request)
    try:
        record, summary = await _summary_for_active(request, conversation)
        if not record or not summary: raise WorkspaceError()
        frame = await asyncio.to_thread(services.analysis.read, services.files.path_for(record), record.extension)
        chart_path = await asyncio.to_thread(services.charts.generate, frame, services.settings.outputs_dir, conversation.conversation_id, chart_type)
        artifact = services.artifacts.register(conversation.conversation_id, record.file_id, "chart_png", chart_path.name, chart_path, {"chart_type": chart_type, "source_name": record.original_name})
        conversation.artifact_ids.append(artifact.artifact_id); services.workspace.update(conversation); services.workspace.increment("charts_generated")
        return _response(request, conversation, notice=f"{chart_type.title()}-график создан.")
    except WorkspaceError as exc: return _response(request, conversation, error=exc.user_message)


@router.post("/report")
async def report(request: Request):
    services = _services(request); conversation = _conversation(request)
    try:
        record, summary = await _summary_for_active(request, conversation)
        if not record or not summary: raise WorkspaceError()
        report_path = await asyncio.to_thread(services.reports.generate, services.settings.outputs_dir, conversation.conversation_id, record.original_name, summary, services.analysis.concise_findings(summary), None)
        artifact = services.artifacts.register(conversation.conversation_id, record.file_id, "report_docx", report_path.name, report_path)
        conversation.artifact_ids.append(artifact.artifact_id); services.workspace.update(conversation); services.workspace.increment("reports_generated")
        return _response(request, conversation, notice="DOCX-отчёт создан.")
    except WorkspaceError as exc: return _response(request, conversation, error=exc.user_message)


@router.post("/summary")
async def summary(request: Request):
    services = _services(request); conversation = _conversation(request)
    try:
        record, dataset = await _summary_for_active(request, conversation)
        if not record or not dataset: raise WorkspaceError()
        await _save_summary(request, conversation, record.file_id, record.original_name, dataset)
        return _response(request, conversation, notice="Markdown summary создан.")
    except WorkspaceError as exc: return _response(request, conversation, error=exc.user_message)


@router.get("/artifacts/{artifact_id}/view")
async def view_chart(request: Request, artifact_id: UUID):
    services = _services(request); conversation = _conversation(request)
    try:
        artifact = services.artifacts.get(artifact_id, conversation.conversation_id)
        if artifact.type != "chart_png":
            raise ArtifactNotFoundError()
        return FileResponse(services.artifacts.path_for(artifact), media_type="image/png", headers={"Content-Disposition": "inline"})
    except WorkspaceError as exc:
        return _response(request, conversation, error=exc.user_message)


@router.get("/artifacts/{artifact_id}")
async def download(request: Request, artifact_id: UUID):
    services = _services(request); conversation = _conversation(request)
    try:
        artifact = services.artifacts.get(artifact_id, conversation.conversation_id)
        services.workspace.increment("analysis_requests")
        media_type = "image/png" if artifact.type == "chart_png" else "application/octet-stream"
        return FileResponse(services.artifacts.path_for(artifact), filename=artifact.name, media_type=media_type)
    except WorkspaceError as exc:
        return _response(request, conversation, error=exc.user_message)
