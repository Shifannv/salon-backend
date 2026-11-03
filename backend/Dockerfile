FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN python -m pip install -r requirements.txt && python -m pip check

COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./

ARG SOURCE_COMMIT=unknown
LABEL org.opencontainers.image.revision=$SOURCE_COMMIT \
      org.opencontainers.image.source="https://github.com/Shifannv/salon-backend"
RUN python -c "import pathlib,re,sys; v=sys.argv[1]; assert v == 'unknown' or re.fullmatch('[0-9a-f]{40}',v); pathlib.Path('/app/build-commit').write_text(v,encoding='ascii')" "$SOURCE_COMMIT" \
    && chmod 444 /app/build-commit

# Precompile app bytecode so a cold instance does not compile it on every start.
# The image is immutable, so unchecked-hash pycs also skip the source timestamp checks.
RUN python -m compileall -q -j 0 --invalidation-mode unchecked-hash app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8000'), timeout=3).read()"

# --ws none: the API has no WebSocket routes, and loading WebSocket support adds to cold start.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --ws none --proxy-headers --forwarded-allow-ips='*'"]
