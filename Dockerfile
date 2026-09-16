FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app
RUN addgroup --system workspace && adduser --system --ingroup workspace workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=workspace:workspace app ./app
COPY --chown=workspace:workspace templates ./templates
COPY --chown=workspace:workspace static ./static
COPY --chown=workspace:workspace scripts ./scripts
RUN mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/metadata /tmp/matplotlib && chown -R workspace:workspace /app /tmp/matplotlib
USER workspace
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
