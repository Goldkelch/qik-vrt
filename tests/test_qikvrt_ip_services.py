# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import unittest

from src.qikvrt_ip_services import (
    AuthoritativeDNSZone,
    DNSRecord,
    DNS_RESPONSE_ANSWER,
    DNS_RESPONSE_NODATA,
    DNS_RESPONSE_NXDOMAIN,
    DNS_RESPONSE_REFUSED,
    ManagedObject,
    ReadOnlyMIB,
    SNMP_END_OF_MIB_VIEW,
    SNMP_NO_SUCH_OBJECT,
    SNMP_SET_BLOCKED,
    canonical_dns_name,
    canonical_oid,
)


class DNSFoundationTests(unittest.TestCase):
    def setUp(self):
        self.zone = AuthoritativeDNSZone(
            "mesh.qikvrt.",
            1,
            (
                DNSRecord("mesh.qikvrt.", "SOA", 300, "ns.mesh.qikvrt. hostmaster.mesh.qikvrt. 1 300 60 3600 60"),
                DNSRecord("mesh.qikvrt.", "NS", 300, "ns.mesh.qikvrt."),
                DNSRecord("ns.mesh.qikvrt.", "A", 60, "10.0.0.1"),
                DNSRecord("node.mesh.qikvrt.", "A", 60, "10.0.0.2"),
                DNSRecord("node.mesh.qikvrt.", "TXT", 60, "qikvrt-node-v1"),
            ),
        )

    def test_canonical_dns_name_is_absolute_ascii(self):
        self.assertEqual(canonical_dns_name("NODE.Mesh.QIKVRT."), "node.mesh.qikvrt.")
        with self.assertRaises(ValueError):
            canonical_dns_name("node.mesh.qikvrt")
        with self.assertRaises(ValueError):
            canonical_dns_name("bad_name.mesh.qikvrt.")

    def test_authoritative_answers_and_refusals_remain_distinct(self):
        answer = self.zone.query("node.mesh.qikvrt.", "A")
        self.assertEqual(answer.status, DNS_RESPONSE_ANSWER)
        self.assertTrue(answer.authoritative)
        self.assertEqual(answer.answers[0].rdata, "10.0.0.2")
        self.assertEqual(self.zone.query("node.mesh.qikvrt.", "AAAA").status, DNS_RESPONSE_NODATA)
        self.assertEqual(self.zone.query("absent.mesh.qikvrt.", "A").status, DNS_RESPONSE_NXDOMAIN)
        self.assertEqual(self.zone.query("other.example.", "A").status, DNS_RESPONSE_REFUSED)

    def test_zone_digest_changes_when_serial_changes(self):
        later = AuthoritativeDNSZone(
            "mesh.qikvrt.",
            2,
            self.zone.records,
        )
        self.assertNotEqual(self.zone.digest, later.digest)


class SNMPFoundationTests(unittest.TestCase):
    def setUp(self):
        self.mib = ReadOnlyMIB((
            ManagedObject((1, 3, 6, 1, 2, 1, 1, 1, 0), "OctetString", "QIK-VRT virtual mesh"),
            ManagedObject((1, 3, 6, 1, 2, 1, 1, 3, 0), "Integer32", 1),
            ManagedObject((1, 3, 6, 1, 4, 1, 55555, 1, 0), "OctetString", "qikvrt-ip-services-v1"),
        ))

    def test_oid_parser_and_get_are_deterministic(self):
        self.assertEqual(canonical_oid("1.3.6.1"), (1, 3, 6, 1))
        result = self.mib.get("1.3.6.1.2.1.1.1.0")
        self.assertEqual(result.status, "VALUE")
        self.assertEqual(result.object.value, "QIK-VRT virtual mesh")
        self.assertEqual(self.mib.get("1.3.6.1.2.1.1.2.0").status, SNMP_NO_SUCH_OBJECT)

    def test_next_bulk_and_set_boundary(self):
        next_result = self.mib.get_next("1.3.6.1.2.1.1.1.0")
        self.assertEqual(next_result.object.oid, (1, 3, 6, 1, 2, 1, 1, 3, 0))
        bulk = self.mib.get_bulk("1.3.6.1.2.1.1.1.0", 4)
        self.assertEqual(bulk[-1].status, SNMP_END_OF_MIB_VIEW)
        self.assertFalse(self.mib.set_is_permitted())
        self.assertEqual(self.mib.set_result()["state"], SNMP_SET_BLOCKED)
        self.assertFalse(self.mib.set_result()["ordinary_release"])


if __name__ == "__main__":
    unittest.main()
