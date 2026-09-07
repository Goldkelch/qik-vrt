FROM debian:bookworm-slim AS m68000-builder

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc-m68k-linux-gnu=4:12.2.0-5 \
      binutils-m68k-linux-gnu=2.40-2 \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY src/m68000/qikvrt_terminal_bootstrap.c /src/qikvrt_terminal_bootstrap.c
RUN mkdir -p /out \
    && m68k-linux-gnu-gcc \
      -std=c90 -pedantic-errors -Wall -Wextra -Werror -Os -m68000 \
      -ffreestanding -fno-builtin -fno-pic -fno-stack-protector \
      -c /src/qikvrt_terminal_bootstrap.c -o /out/qikvrt_terminal_bootstrap.o \
    && m68k-linux-gnu-objcopy -j .text -O binary \
      /out/qikvrt_terminal_bootstrap.o /out/qikvrt_terminal_bootstrap.bin \
    && m68k-linux-gnu-objdump -f -dr /out/qikvrt_terminal_bootstrap.o \
      > /out/qikvrt_terminal_bootstrap.objdump.txt \
    && grep -Eiq 'm68k|mc68000' /out/qikvrt_terminal_bootstrap.objdump.txt \
    && cd /out \
    && sha256sum qikvrt_terminal_bootstrap.bin > qikvrt_terminal_bootstrap.bin.sha256 \
    && sha256sum qikvrt_terminal_bootstrap.o > qikvrt_terminal_bootstrap.o.sha256 \
    && test -s qikvrt_terminal_bootstrap.bin


FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG QIKVRT_EXACT_SUBJECT_SHA=UNBOUND
ENV DISPLAY=:99 \
    HOME=/var/lib/qikvrt/state/home \
    QIKVRT_HTTP_PORT=8771 \
    QIKVRT_NOVNC_PORT=6080 \
    QIKVRT_PROXY_PORT=8080 \
    QIKVRT_PROXY_HOST=127.0.0.1 \
    QIKVRT_SMTP_PORT=1025 \
    QIKVRT_DNS_PORT=1053 \
    QIKVRT_SNMP_PORT=1161 \
    QIKVRT_SSH_PORT=2222 \
    QIKVRT_POSTGRES_PORT=5432 \
    QIKVRT_GIT_MIRROR_PORT=9418 \
    QIKVRT_START_URL=https://github.com/Goldkelch/qik-vrt \
    QIKVRT_PROFILE_DIR=/var/lib/qikvrt/profile \
    QIKVRT_STATE_DIR=/var/lib/qikvrt/state \
    QIKVRT_RUNTIME_ID=qikvrt-cloud-transputer-v1 \
    QIKVRT_IMAGE_SUBJECT_SHA=${QIKVRT_EXACT_SUBJECT_SHA}

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates firefox-esr python3 python3-minimal git zip \
      xvfb x11vnc novnc websockify dbus-x11 procps curl \
      openbox xterm \
      dropbear-bin=2022.83-1+deb12u3 \
      postgresql-15 postgresql-client-15 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --home-dir /var/lib/qikvrt/state/home \
         --no-create-home --shell /bin/sh qikvrt

WORKDIR /opt/qikvrt
COPY . /opt/qikvrt
COPY --from=m68000-builder /out/ /opt/qikvrt/assets/m68000/

RUN mkdir -p \
      /opt/qikvrt/assets/bootstrap-profile/extensions \
      /var/lib/qikvrt/profile \
      /var/lib/qikvrt/state \
    && cd browser/firefox/qikvrt-terminal \
    && zip -qr /opt/qikvrt/assets/bootstrap-profile/extensions/qikvrt-ai-terminal@goldkelch.local.xpi . \
    && printf '%s\n' \
      'user_pref("browser.shell.checkDefaultBrowser", false);' \
      'user_pref("browser.startup.homepage", "https://github.com/Goldkelch/qik-vrt");' \
      'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);' \
      'user_pref("datareporting.policy.dataSubmissionEnabled", false);' \
      'user_pref("browser.sessionstore.resume_from_crash", true);' \
      > /opt/qikvrt/assets/bootstrap-profile/user.js \
    && chown -R qikvrt:qikvrt \
      /opt/qikvrt/assets \
      /var/lib/qikvrt/profile \
      /var/lib/qikvrt/state

COPY deploy/universal-terminal/entrypoint.sh /usr/local/bin/qikvrt-universal-terminal
COPY deploy/universal-terminal/runtime-health.sh /usr/local/bin/qikvrt-runtime-health
RUN chmod +x /usr/local/bin/qikvrt-universal-terminal /usr/local/bin/qikvrt-runtime-health

VOLUME ["/var/lib/qikvrt/profile", "/var/lib/qikvrt/state"]
EXPOSE 6080 8080
HEALTHCHECK --interval=15s --timeout=15s --start-period=60s --retries=8 \
  CMD ["/usr/local/bin/qikvrt-runtime-health"]

USER 10001:10001
ENTRYPOINT ["/usr/local/bin/qikvrt-universal-terminal"]
