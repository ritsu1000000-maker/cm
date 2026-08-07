FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    git \
    nano \
    nodejs \
    npm \
    procps \
    python3 \
    python3-pip \
    python3-venv \
    supervisor \
    tini \
    ttyd \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash sandbox \
    && mkdir -p /opt/botbox /workspace \
    && chown -R sandbox:sandbox /opt/botbox /workspace /home/sandbox

COPY --chown=sandbox:sandbox runtime/ /opt/botbox/

RUN chmod +x \
    /opt/botbox/entrypoint.sh \
    /opt/botbox/run-ttyd.sh \
    /opt/botbox/run-bot.sh \
    /opt/botbox/botctl \
    && ln -s /opt/botbox/botctl /usr/local/bin/botctl

USER sandbox
WORKDIR /workspace
ENV HOME=/home/sandbox
ENV TERM=xterm-256color

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/botbox/entrypoint.sh"]
