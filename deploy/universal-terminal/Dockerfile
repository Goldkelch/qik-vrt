FROM debian:bookworm-slim AS qikvrt-m68k-builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      binutils-m68k-linux-gnu gcc libc6-dev gcc-m68k-linux-gnu libc6-dev-m68k-cross \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY deploy/universal-terminal/qikvrt_ip_bootstrap.c /src/qikvrt_ip_bootstrap.c
COPY src/cloud_transputer/m68k_contract_probe.c /src/m68k_contract_probe.c
RUN set -eux; \
    mkdir -p /out/m68k; \
    gcc -std=c90 -pedantic-errors -Wall -Wextra -Werror -O2 /src/qikvrt_ip_bootstrap.c -o /out/qikvrt-ip-bootstrap; \
    m68k-linux-gnu-gcc -m68000 -std=c90 -pedantic-errors -Wall -Wextra -Werror -O2 -c /src/qikvrt_ip_bootstrap.c -o /out/m68k/qikvrt_ip_bootstrap.o; \
    m68k-linux-gnu-gcc -m68000 -static -std=c90 -pedantic-errors -Wall -Wextra -Werror -O2 /src/m68k_contract_probe.c -o /out/qikvrt-m68k-selftest; \
    m68k-linux-gnu-readelf -h /out/qikvrt-m68k-selftest > /out/m68k/qikvrt-m68k-selftest.readelf.txt; \
    m68k-linux-gnu-objdump -dr /out/qikvrt-m68k-selftest > /out/m68k/qikvrt-m68k-selftest.objdump.txt; \
    m68k-linux-gnu-readelf -h /out/m68k/qikvrt_ip_bootstrap.o > /out/m68k/qikvrt_ip_bootstrap.readelf.txt; \
    (cd /out && sha256sum qikvrt-m68k-selftest > m68k/qikvrt-m68k-selftest.sha256); \
    (cd /out/m68k && sha256sum qikvrt_ip_bootstrap.o > qikvrt_ip_bootstrap.sha256)

FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive DISPLAY=:99 \
    QIKVRT_HTTP_HOST=127.0.0.1 QIKVRT_HTTP_PORT=8771 QIKVRT_NOVNC_PORT=6080 \
    QIKVRT_START_URL=http://qikvrt-gateway:8080/qik-vrt/mesh/v1/ \
    QIKVRT_PROFILE_DIR=/var/lib/qikvrt/profile QIKVRT_STATE_DIR=/var/lib/qikvrt/state \
    QIKVRT_RUNTIME_ID=qikvrt-firefox-terminal QIKVRT_SERVICE_MODE=terminal \
    QIKVRT_MC68000_CC=m68k-linux-gnu-gcc QIKVRT_MC68000_RUNNER=qemu-m68k
RUN apt-get update && apt-get install -y --no-install-recommends \
      bind9 binutils-m68k-linux-gnu ca-certificates curl dbus-x11 dnsutils firefox-esr git \
      gcc-m68k-linux-gnu libc6-dev-m68k-cross make nginx-light novnc openssh-server \
      postgresql postgresql-client procps python3 python3-minimal qemu-user snmp snmpd \
      util-linux websockify x11-utils x11vnc xvfb zip \
    && test -s /usr/share/novnc/vnc.html && test -s /usr/share/novnc/core/rfb.js \
    && command -v m68k-linux-gnu-gcc && command -v qemu-m68k \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/qikvrt
COPY . /opt/qikvrt
COPY --from=qikvrt-m68k-builder /out/qikvrt-ip-bootstrap /usr/local/bin/qikvrt-ip-bootstrap
COPY --from=qikvrt-m68k-builder /out/qikvrt-m68k-selftest /usr/local/bin/qikvrt-m68k-selftest
COPY --from=qikvrt-m68k-builder /out/m68k /opt/qikvrt/runtime/m68k
RUN mkdir -p /opt/qikvrt/runtime/bootstrap-profile/extensions /opt/qikvrt/runtime/logs \
    /var/lib/qikvrt/profile /var/lib/qikvrt/state /var/lib/qikvrt/smtp /var/lib/qikvrt/ssh \
    /var/lib/qikvrt/postgres /var/lib/qikvrt/mirror /var/lib/qikvrt/personal-posix \
    && (cd browser/firefox/qikvrt-terminal && zip -qr /opt/qikvrt/runtime/bootstrap-profile/extensions/qikvrt-ai-terminal@goldkelch.local.xpi .) \
    && printf '%s\n' 'user_pref("browser.shell.checkDefaultBrowser", false);' \
      'user_pref("browser.startup.homepage", "http://qikvrt-gateway:8080/qik-vrt/mesh/v1/");' \
      'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);' \
      'user_pref("datareporting.policy.dataSubmissionEnabled", false);' \
      'user_pref("browser.sessionstore.resume_from_crash", true);' \
      > /opt/qikvrt/runtime/bootstrap-profile/user.js
COPY deploy/universal-terminal/entrypoint.sh /usr/local/bin/qikvrt-universal-terminal
COPY deploy/universal-terminal/cloud-entrypoint.sh /usr/local/bin/qikvrt-cloud-terminal
COPY deploy/universal-terminal/runtime-health.sh /usr/local/bin/qikvrt-runtime-health
COPY deploy/universal-terminal/service-entrypoint.sh /usr/local/bin/qikvrt-service-entrypoint
COPY deploy/universal-terminal/mirror-bootstrap.sh /usr/local/bin/qikvrt-mirror-bootstrap
COPY deploy/universal-terminal/qikvrt_smtpd.py /usr/local/bin/qikvrt-smtpd
RUN chmod +x /usr/local/bin/qikvrt-* \
    && python3 - <<'PY'
import json
p=json.load(open('/opt/qikvrt/policy/QIKVRT_CLOUD_TRANSPUTER_V1.json'))
assert p['architecture']=='MC68000'
assert p['boundary_contract']['decision_codes']=={'NOOP':0,'HOLD':1,'REOBSERVE':2,'REQUEST_AUTHORITY':3}
assert p['boundary_contract']['binary_weights']==[1,2,4]
assert p['effect_ack_protocol']['state_codes']=={'EFFECT_NACK':0,'EFFECT_ACK_CONTINUE':1,'EFFECT_ACK_ISOLATE':2,'EFFECT_ACK_BLOCK':3,'EFFECT_ACK_DONE':4}
assert p['effect_ack_protocol']['register']=='D4'
assert p['overlay_model']['banks']==4
assert p['ip_bootstrap']['subnet']=='10.73.0.0/24'
PY
EXPOSE 6080 8080 8771 2222 2525 5353 9418 1161 5432 7331/udp
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 CMD ["/usr/local/bin/qikvrt-runtime-health"]
ENTRYPOINT ["/usr/local/bin/qikvrt-service-entrypoint"]
