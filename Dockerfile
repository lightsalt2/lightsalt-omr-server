FROM eclipse-temurin:21-jre-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    AUDIVERIS_BIN=/opt/audiveris/bin/Audiveris

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip curl ca-certificates jq unzip \
    libfreetype6 fontconfig libxext6 libxrender1 libxtst6 libxi6 \
    libasound2 libgtk-3-0 fonts-dejavu-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# GitHub Audiveris 공식 릴리스의 Linux .deb 설치 파일 사용
# 최신 릴리스의 자산 구성이 바뀌면 빌드가 실패할 수 있습니다.
RUN set -eux; \
    url="$(curl -fsSL https://api.github.com/repos/Audiveris/audiveris/releases/latest \
      | jq -r '[.assets[] | select(.name | endswith(".deb")) | .browser_download_url][0] // empty')"; \
    test -n "$url"; \
    curl -fL "$url" -o /tmp/audiveris.deb; \
    apt-get update; \
    apt-get install -y /tmp/audiveris.deb; \
    rm -f /tmp/audiveris.deb; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
COPY main.py .
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 10000
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
