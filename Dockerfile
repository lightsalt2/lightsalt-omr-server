
FROM eclipse-temurin:25-jdk AS audiveris-build

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone --depth 1 https://github.com/Audiveris/audiveris.git

WORKDIR /build/audiveris

RUN java -version && \
    javac -version && \
    ./gradlew --no-daemon :app:installDist && \
    find /build/audiveris/app/build/install -maxdepth 3 -type f | head -30 && \
    mkdir -p /opt/audiveris && \
    dist="$(find /build/audiveris/app/build/install -mindepth 1 -maxdepth 1 -type d | head -n 1)" && \
    test -n "$dist" && \
    test -d "$dist/bin" && \
    cp -a "$dist/." /opt/audiveris/ && \
    launcher="$(find /opt/audiveris/bin -maxdepth 1 -type f ! -name '*.bat' | head -n 1)" && \
    test -n "$launcher" && \
    chmod +x "$launcher" && \
    ln -s "$(basename "$launcher")" /opt/audiveris/bin/Audiveris 2>/dev/null || test -f /opt/audiveris/bin/Audiveris

FROM eclipse-temurin:25-jre

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    AUDIVERIS_BIN=/opt/audiveris/bin/Audiveris

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    ca-certificates \
    libfreetype6 fontconfig \
    libxext6 libxrender1 libxtst6 libxi6 \
    libasound2t64 libgtk-3-0 \
    fonts-dejavu-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY --from=audiveris-build \
    /opt/audiveris \
    /opt/audiveris

WORKDIR /app

COPY requirements.txt .

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
