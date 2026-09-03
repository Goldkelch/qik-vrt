FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    QIKVRT_HTTP_PORT=8771 \
    QIKVRT_NOVNC_PORT=6080 \
    QIKVRT_START_URL=https://goldkelch.github.io/qik-vrt/

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates firefox-esr python3 python3-minimal git zip \
      xvfb x11vnc novnc websockify dbus-x11 procps curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/qikvrt
COPY . /opt/qikvrt

RUN mkdir -p /opt/qikvrt/runtime/profile/extensions /opt/qikvrt/runtime/logs \
    && cd browser/firefox/qikvrt-terminal \
    && zip -qr /opt/qikvrt/runtime/profile/extensions/qikvrt-ai-terminal@goldkelch.local.xpi . \
    && printf '%s\n' \
      'user_pref("browser.shell.checkDefaultBrowser", false);' \
      'user_pref("browser.startup.homepage", "https://goldkelch.github.io/qik-vrt/");' \
      'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);' \
      'user_pref("datareporting.policy.dataSubmissionEnabled", false);' \
      > /opt/qikvrt/runtime/profile/user.js

COPY deploy/universal-terminal/entrypoint.sh /usr/local/bin/qikvrt-universal-terminal
RUN chmod +x /usr/local/bin/qikvrt-universal-terminal

EXPOSE 6080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
  CMD curl -fsS http://127.0.0.1:8771/.well-known/effect-ack >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/qikvrt-universal-terminal"]
