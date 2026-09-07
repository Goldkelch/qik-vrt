# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    QIKVRT_HTTP_PORT=8771 \
    QIKVRT_NOVNC_PORT=6080 \
    QIKVRT_PROXY_PORT=8080 \
    QIKVRT_SSH_PORT=2222 \
    QIKVRT_SMTP_PORT=2525 \
    QIKVRT_DNS_PORT=5353 \
    QIKVRT_SNMP_PORT=1161 \
    QIKVRT_SQL_PORT=5432 \
    QIKVRT_PROFILE_DIR=/var/lib/qikvrt/profile \
    QIKVRT_STATE_DIR=/var/lib/qikvrt/state \
    QIKVRT_AUTHORITY_MIRROR_DIR=/var/lib/qikvrt/mirror/authority.git \
    QIKVRT_PERSONAL_POSIX_DIR=/var/lib/qikvrt/personal-posix \
    QIKVRT_MAIL_DIR=/var/lib/qikvrt/mail \
    QIKVRT_RUNTIME_ID=qikvrt-cloud-transputer-1 \
    QIKVRT_MESH_PUBLIC_URL=https://goldkelch.github.io/qik-vrt/cloud-transputer/ \
    QIKVRT_MESH_DOMAIN=qikvrt.mesh.local \
    QIKVRT_START_URL=https://goldkelch.github.io/qik-vrt/

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git zip file procps sed \
      firefox-esr fonts-dejavu-core xvfb x11vnc novnc websockify dbus-x11 \
      nginx openssh-server \
      postgresql postgresql-client \
      dnsmasq dnsutils \
      snmpd snmp \
      qemu-user gcc-m68k-linux-gnu libc6-dev-m68k-cross \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash qikvrt \
    && passwd -l qikvrt \
    && mkdir -p /opt/qikvrt/runtime/bootstrap-profile/extensions \
                /opt/qikvrt/runtime/cloud-transputer-logs \
                /var/lib/qikvrt/profile /var/lib/qikvrt/state \
                /var/lib/qikvrt/mirror /var/lib/qikvrt/personal-posix \
                /var/lib/qikvrt/mail

WORKDIR /opt/qikvrt
COPY . /opt/qikvrt

RUN cd browser/firefox/qikvrt-terminal \
    && zip -qr /opt/qikvrt/runtime/bootstrap-profile/extensions/qikvrt-ai-terminal@goldkelch.local.xpi . \
    && printf '%s\n' \
      'user_pref("browser.shell.checkDefaultBrowser", false);' \
      'user_pref("browser.startup.homepage", "https://goldkelch.github.io/qik-vrt/");' \
      'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);' \
      'user_pref("datareporting.policy.dataSubmissionEnabled", false);' \
      'user_pref("browser.sessionstore.resume_from_crash", true);' \
      > /opt/qikvrt/runtime/bootstrap-profile/user.js \
    && cp deploy/cloud-transputer/entrypoint.sh /usr/local/bin/qikvrt-cloud-transputer \
    && cp deploy/cloud-transputer/runtime-health.sh /usr/local/bin/qikvrt-cloud-transputer-health \
    && cp deploy/cloud-transputer/authority-mirror-refresh.sh /usr/local/bin/qikvrt-authority-mirror-refresh \
    && chmod 0755 /usr/local/bin/qikvrt-cloud-transputer \
                  /usr/local/bin/qikvrt-cloud-transputer-health \
                  /usr/local/bin/qikvrt-authority-mirror-refresh \
                  /opt/qikvrt/src/cloud_transputer/smtpd.py

VOLUME ["/var/lib/qikvrt/profile", "/var/lib/qikvrt/state", "/var/lib/qikvrt/mirror", "/var/lib/qikvrt/personal-posix", "/var/lib/qikvrt/mail"]

EXPOSE 8080/tcp 2222/tcp 2525/tcp 5353/tcp 5353/udp 1161/udp 5432/tcp

HEALTHCHECK --interval=15s --timeout=10s --start-period=90s --retries=6 \
  CMD ["/usr/local/bin/qikvrt-cloud-transputer-health"]

ENTRYPOINT ["/usr/local/bin/qikvrt-cloud-transputer"]
