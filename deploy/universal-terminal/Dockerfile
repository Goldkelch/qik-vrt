FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    QIKVRT_HTTP_PORT=8771 \
    QIKVRT_NOVNC_PORT=6080 \
    QIKVRT_START_URL=https://arxiv.org/ \
    QIKVRT_PROFILE_DIR=/var/lib/qikvrt/profile \
    QIKVRT_STATE_DIR=/var/lib/qikvrt/state \
    QIKVRT_RUNTIME_ID=qikvrt-firefox-terminal

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates firefox-esr python3 python3-minimal git zip \
      xvfb x11vnc novnc websockify dbus-x11 procps curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/qikvrt
COPY . /opt/qikvrt

RUN mkdir -p /opt/qikvrt/runtime/bootstrap-profile/extensions /opt/qikvrt/runtime/logs \
    /var/lib/qikvrt/profile /var/lib/qikvrt/state \
    && cd browser/firefox/qikvrt-terminal \
    && zip -qr /opt/qikvrt/runtime/bootstrap-profile/extensions/qikvrt-ai-terminal@goldkelch.local.xpi . \
    && printf '%s\n' \
      'user_pref("browser.shell.checkDefaultBrowser", false);' \
      'user_pref("browser.startup.homepage", "https://arxiv.org/");' \
      'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);' \
      'user_pref("datareporting.policy.dataSubmissionEnabled", false);' \
      'user_pref("browser.sessionstore.resume_from_crash", true);' \
      > /opt/qikvrt/runtime/bootstrap-profile/user.js

COPY deploy/universal-terminal/entrypoint.sh /usr/local/bin/qikvrt-universal-terminal
COPY deploy/universal-terminal/runtime-health.sh /usr/local/bin/qikvrt-runtime-health
RUN chmod +x /usr/local/bin/qikvrt-universal-terminal /usr/local/bin/qikvrt-runtime-health

VOLUME ["/var/lib/qikvrt/profile", "/var/lib/qikvrt/state"]
EXPOSE 6080
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD ["/usr/local/bin/qikvrt-runtime-health"]

ENTRYPOINT ["/usr/local/bin/qikvrt-universal-terminal"]
