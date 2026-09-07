import importlib.util
import pathlib
import socket
import struct
import tempfile
import threading
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src/qikvrt_universal_service_plane.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_universal_service_plane", MODULE_PATH)
assert SPEC and SPEC.loader
plane = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plane)


class ServicePlaneTests(unittest.TestCase):
    def test_dns_authoritative_local_a_and_nxdomain(self):
        response = plane.build_dns_response(plane.dns_query_packet())
        self.assertEqual(struct.unpack("!H", response[6:8])[0], 1)
        self.assertEqual(response[-4:], socket.inet_aton("127.0.0.1"))
        missing = plane.build_dns_response(plane.dns_query_packet("outside.example"))
        flags = struct.unpack("!H", missing[2:4])[0]
        self.assertEqual(flags & 0x000F, 3)

    def test_snmp_v2c_sysdescr(self):
        response = plane.build_snmp_response(plane.snmp_get_packet())
        self.assertIn(plane.SYS_DESCR.encode("utf-8"), response)

    def test_smtp_refuses_relay_and_persists_local_mail(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = plane.ReuseThreadingTCPServer(("127.0.0.1", 0), plane.SMTPHandler)
            server.mail_dir = pathlib.Path(temporary)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with socket.create_connection(server.server_address, timeout=3) as sock:
                    file = sock.makefile("rwb", buffering=0)
                    self.assertTrue(file.readline().startswith(b"220 "))
                    file.write(b"EHLO test\r\n")
                    self.assertTrue(file.readline().startswith(b"250-"))
                    self.assertTrue(file.readline().startswith(b"250 "))
                    file.write(b"MAIL FROM:<sender@qikvrt.local>\r\n")
                    self.assertTrue(file.readline().startswith(b"250 "))
                    file.write(b"RCPT TO:<outside@example.net>\r\n")
                    self.assertTrue(file.readline().startswith(b"550 "))
                    file.write(b"RCPT TO:<user@qikvrt.local>\r\n")
                    self.assertTrue(file.readline().startswith(b"250 "))
                    file.write(b"DATA\r\n")
                    self.assertTrue(file.readline().startswith(b"354 "))
                    file.write(b"Subject: test\r\n\r\nhello\r\n.\r\n")
                    self.assertTrue(file.readline().startswith(b"250 "))
                    file.write(b"QUIT\r\n")
                    self.assertTrue(file.readline().startswith(b"221 "))
                files = list(pathlib.Path(temporary).glob("*.eml"))
                self.assertEqual(len(files), 1)
                self.assertIn(b"hello", files[0].read_bytes())
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
