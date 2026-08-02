FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
ARG INSTALL_AI=false
RUN if [ "$INSTALL_AI" = "true" ]; then pip install --no-cache-dir '.[ai]'; else pip install --no-cache-dir .; fi
EXPOSE 8000
CMD ["uvicorn", "best_gift_search.app:app", "--host", "0.0.0.0", "--port", "8000"]
