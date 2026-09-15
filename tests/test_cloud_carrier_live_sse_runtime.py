# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Permanent RED/GREEN gate for Cloud-Transputer live-monitor delivery."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CloudCarrierLiveSseRuntime(unittest.TestCase):
 def test_repaired_relay_is_present(self):
  p=ROOT/'tools/qikvrt_live_sse.py'; self.assertTrue(p.is_file(),'live SSE relay absent from cloud carrier'); t=p.read_text(); self.assertIn('event: qikvrt',t); self.assertIn('Last-Event-ID',t); self.assertNotIn('time.sleep(',t)
 def test_repaired_extension_consumes_same_event(self):
  t=(ROOT/'browser/firefox/qikvrt-terminal/background.js').read_text(); self.assertIn('source.addEventListener("qikvrt"',t); self.assertIn('qikvrtLastEventId',t); self.assertNotIn('browser.alarms',t)
 def test_container_starts_live_relay_on_loopback(self):
  t=(ROOT/'deploy/universal-terminal/service-entrypoint.sh').read_text()+'\n'+(ROOT/'deploy/universal-terminal/cloud-entrypoint.sh').read_text(); self.assertIn('qikvrt_live_sse.py',t); self.assertIn('127.0.0.1',t); self.assertIn('8787',t)
 def test_runtime_health_checks_live_relay(self):
  t=(ROOT/'deploy/universal-terminal/runtime-health.sh').read_text(); self.assertIn('8787',t); self.assertIn('/events',t)
 def test_xpi_is_built_from_repository_extension(self):
  t=(ROOT/'deploy/universal-terminal/Dockerfile').read_text(); self.assertIn('browser/firefox/qikvrt-terminal',t); self.assertIn('qikvrt-ai-terminal@goldkelch.local.xpi',t)
if __name__=='__main__': unittest.main()
