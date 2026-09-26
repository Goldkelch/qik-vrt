#!/bin/sh
set -eu

# A deliberately restrained Mega-ST/GEM-inspired shell on top of a modern Xfce session.
# This changes presentation only; it does not claim binary or hardware identity with an Atari Mega ST.

if command -v xfconf-query >/dev/null 2>&1; then
  xfconf-query -c xsettings -p /Net/ThemeName -s Default 2>/dev/null || true
  xfconf-query -c xsettings -p /Gtk/FontName -s "DejaVu Sans 10" 2>/dev/null || true
  xfconf-query -c xfwm4 -p /general/theme -s Default 2>/dev/null || true
  xfconf-query -c xfwm4 -p /general/title_font -s "DejaVu Sans Bold 10" 2>/dev/null || true
  xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/color-style -s 0 2>/dev/null || true
  xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/rgba1 -s 0.70 -s 0.70 -s 0.70 -s 1.0 2>/dev/null || true
fi

mkdir -p "$HOME/Desktop" "$HOME/.config/qikvrt"
cat > "$HOME/Desktop/QIK-VRT-Mega-ST.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Atari Mega ST (Hatari)
Comment=Start the Mega-ST hardware environment with the pinned redistributable EmuTOS ROM.
Exec=hatari --machine st --tos /usr/share/qikvrt/emutos/etos256de.img
Icon=computer
Terminal=false
EOF
chmod +x "$HOME/Desktop/QIK-VRT-Mega-ST.desktop"

cat > "$HOME/Desktop/QIK-VRT-Transputer.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=QIK-VRT Universal Terminal
Comment=TEMDD editor and retained Transputer history
Exec=firefox-esr --new-window http://127.0.0.1:8772/AI
Icon=utilities-terminal
Terminal=false
EOF
chmod +x "$HOME/Desktop/QIK-VRT-Transputer.desktop"

cat > "$HOME/Desktop/Modern-Software.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Modern Software
Comment=Open the modern QIK-VRT application substrate.
Exec=xfce4-terminal --title=QIK-VRT --command=/usr/local/bin/qikvrt-modern-shell
Icon=utilities-terminal
Terminal=false
EOF
chmod +x "$HOME/Desktop/Modern-Software.desktop"

cat > /tmp/qikvrt-modern-shell.$$ <<'EOF'
#!/bin/sh
printf '%s\n' 'QIK-VRT modern software envelope'
printf '%s\n' '  native : apt / Debian'
printf '%s\n' '  portable: Flatpak'
printf '%s\n' '  service : Podman / OCI'
printf '%s\n' '  web     : Firefox'
printf '%s\n' '' 'Stay fail closed and keep future open.'
exec ${SHELL:-/bin/sh} -l
EOF
sudo install -m 0755 /tmp/qikvrt-modern-shell.$$ /usr/local/bin/qikvrt-modern-shell 2>/dev/null || true
rm -f /tmp/qikvrt-modern-shell.$$

cat > "$HOME/.config/qikvrt/session-receipt.json" <<EOF
{
  "schema":"qikvrt_megast_session_receipt_v1",
  "visual_shell":"MEGA_ST_GEM_INSPIRED",
  "hatari_present":$(command -v hatari >/dev/null 2>&1 && echo true || echo false),
  "firefox_present":$(command -v firefox-esr >/dev/null 2>&1 && echo true || echo false),
  "podman_present":$(command -v podman >/dev/null 2>&1 && echo true || echo false),
  "flatpak_present":$(command -v flatpak >/dev/null 2>&1 && echo true || echo false),
  "effect_ack_done":false,
  "reason":"session_materialization_is_not_terminal_effect"
}
EOF

# Start the actual client in the graphical session, then observe its window and
# the locally executed C90/Smalltalk/MC68000 paths before reporting runtime ready.
# Wait for the existing service's first durable registration before opening the
# browser. systemd process startup alone does not mean its HTTP listener is ready.
transputer_ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent --max-time 1 http://127.0.0.1:8772/api/directory >/dev/null; then
    transputer_ready=1
    break
  fi
  sleep 1
done
if [ "$transputer_ready" -ne 1 ]; then
  printf '%s\n' 'BLOCK: Universal Transputer terminal did not become ready' >&2
  exit 1
fi
firefox-esr --new-window http://127.0.0.1:8772/AI \
  > "$HOME/.config/qikvrt/firefox.log" 2>&1 &
hatari --machine st --tos /usr/share/qikvrt/emutos/etos256de.img \
  > "$HOME/.config/qikvrt/hatari.log" 2>&1 &
python3 -B /opt/qikvrt/runtime-witness.py > "$HOME/.config/qikvrt/runtime-witness.log" 2>&1 &
