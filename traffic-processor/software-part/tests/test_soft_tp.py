import pytest  # noqa: F401
from scapy.all import ARP, Ether, ICMP, IP, UDP, Raw, SCTP, TCP
import tp_packet_counter


class TestGetJsonPayload:
    def test_ipv4_packet_ports_exist(self):
        fake_direction = 1
        fake_pkt = (
            Ether()
            / IP(src="192.168.100.1", dst="192.168.100.2")
            / UDP(sport=9090, dport=1547)
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        expected_json = {
            "direction": 1,
            "src_ip": "192.168.100.1",
            "dst_ip": "192.168.100.2",
            "src_port": 9090,
            "dst_port": 1547,
            "protocol": "UDP",
            "size": 54,
        }
        assert created_json == expected_json

    def test_ipv4_packet_ports_absent(self):
        fake_direction = 1
        fake_pkt = (
            Ether() / IP(src="192.168.100.1", dst="192.168.100.2") / ICMP()
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        expected_json = {
            "direction": 1,
            "src_ip": "192.168.100.1",
            "dst_ip": "192.168.100.2",
            "src_port": None,
            "dst_port": None,
            "protocol": "ICMP",
            "size": 54,
        }
        assert created_json == expected_json

    def test_not_ipv4_packet(self):
        fake_direction = 1
        fake_pkt = Ether() / ARP()
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        expected_json = {
            "direction": 1,
            "src_ip": None,
            "dst_ip": None,
            "src_port": None,
            "dst_port": None,
            "protocol": None,
            "size": 54,
        }
        assert created_json == expected_json

    def test_direction(self):
        fake_direction_out = 1
        fake_pkt_out = Ether() / ARP()
        created_json_out = tp_packet_counter.get_json_payload(
            fake_pkt_out, fake_direction_out
        )

        fake_direction_in = 0
        fake_pkt_in = Ether() / ARP()
        created_json_in = tp_packet_counter.get_json_payload(
            fake_pkt_in, fake_direction_in
        )

        assert created_json_in["direction"] == 0
        assert created_json_out["direction"] == 1

    def test_size_basic(self):
        fake_direction = 1
        fake_pkt = (
            Ether()
            / IP(src="192.168.100.1", dst="192.168.100.2")
            / ICMP()
            / Raw("1234567890" * 11)
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        expected_json = {
            "direction": 1,
            "src_ip": "192.168.100.1",
            "dst_ip": "192.168.100.2",
            "src_port": None,
            "dst_port": None,
            "protocol": "ICMP",
            "size": 164,
        }
        assert created_json == expected_json

    def test_size_minimal(self):
        fake_direction = 1
        fake_pkt = Ether()
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        expected_json = {
            "direction": 1,
            "src_ip": None,
            "dst_ip": None,
            "src_port": None,
            "dst_port": None,
            "protocol": None,
            "size": 26,
        }
        assert created_json == expected_json

    def test_protocol_icmp(self):
        fake_direction = 1
        fake_pkt = (
            Ether() / IP(src="192.168.100.1", dst="192.168.100.2") / ICMP()
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        assert created_json["protocol"] == "ICMP"

    def test_protocol_tcp(self):
        fake_direction = 1
        fake_pkt = (
            Ether() / IP(src="192.168.100.1", dst="192.168.100.2") / TCP()
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        assert created_json["protocol"] == "TCP"

    def test_protocol_udp(self):
        fake_direction = 1
        fake_pkt = (
            Ether() / IP(src="192.168.100.1", dst="192.168.100.2") / UDP()
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        assert created_json["protocol"] == "UDP"

    def test_protocol_sctp(self):
        fake_direction = 1
        fake_pkt = (
            Ether() / IP(src="192.168.100.1", dst="192.168.100.2") / SCTP()
        )
        created_json = tp_packet_counter.get_json_payload(
            fake_pkt, fake_direction
        )
        assert created_json["protocol"] == "SCTP"
