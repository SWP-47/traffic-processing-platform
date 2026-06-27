import pytest
from scapy.all import *
import json
import queue
from jsonschema import validate, ValidationError
import cn_demo_1


class TestMakeJsonForCnss:
    def test_correct_data_real_packets(self):
        fake_packets_to_send = [
            {
                "direction": 1,   
                "src_ip": "192.168.100.1",
                "dst_ip": "192.168.100.2",
                "src_port": 9090,
                "dst_port": 1547,
            },
            {
                "direction": 0,   
                "src_ip": "192.168.100.3",
                "dst_ip": "192.168.100.4",
                "src_port": None,
                "dst_port": None,
            }
        ]
        fake_sequence = 12

        created_json = cn_demo_1.make_json_for_cnss(fake_packets_to_send, fake_sequence)  

        assert created_json["channel_id"] == cn_demo_1.CHANNEL_ID
        assert isinstance(created_json["timestamp"], int)
        assert created_json["timestamp"] >= 10**9 and created_json["timestamp"] < 10**10
        assert created_json["sequence"] == fake_sequence
        assert created_json["window_ms"] == int(cn_demo_1.TIME_WINDOW)
        assert created_json["packets"] == fake_packets_to_send


    def test_correct_data_no_packets(self):
        fake_packets_to_send = []
        fake_sequence = 123

        created_json = cn_demo_1.make_json_for_cnss(fake_packets_to_send, fake_sequence)  

        assert created_json["channel_id"] == cn_demo_1.CHANNEL_ID
        assert isinstance(created_json["timestamp"], int)
        assert created_json["timestamp"] >= 10**9 and created_json["timestamp"] < 10**10
        assert created_json["sequence"] == fake_sequence
        assert created_json["window_ms"] == int(cn_demo_1.TIME_WINDOW)
        assert created_json["packets"] == fake_packets_to_send


    
class TestProcessPacket:
    def setup_method(self):
        while not cn_demo_1.packet_queue.empty():
            cn_demo_1.packet_queue.get_nowait()
    

    def test_correct_packet(self):
        fake_pkt_payload = {
                "direction": 1,   
                "src_ip": "192.168.100.1",
                "dst_ip": "192.168.100.2",
                "src_port": 9090,
                "dst_port": 1547,
            }
        fake_pkt_payload_bin = json.dumps(fake_pkt_payload).encode('utf-8')
        fake_pkt = Ether() / IP() / UDP() / Raw(load=fake_pkt_payload_bin)

        cn_demo_1.process_packet(fake_pkt)

        assert not cn_demo_1.packet_queue.empty()

    
    def test_packet_without_Raw_layer(self):
        fake_pkt = Ether() / IP() / UDP()

        cn_demo_1.process_packet(fake_pkt)

        assert cn_demo_1.packet_queue.empty()

    
    def test_payload_is_not_json(self):
        fake_pkt_payload = '"direction": 1, "src_ip": "192.168.100.1", "dst_ip": "192.168.100.2", "src_port": 9090, "dst_port": 1547'
        fake_pkt = Ether() / IP() / UDP() / Raw(load=fake_pkt_payload)

        cn_demo_1.process_packet(fake_pkt)

        assert cn_demo_1.packet_queue.empty()


    def test_payload_is_invalid_json(self):
        fake_pkt_payload = { 
                "src_ip": "192.168.100.1",
                "dst_ip": "192.168.100.2",
                "src_port": 9090,
                "dst_port": 1547,
            }
        fake_pkt_payload_bin = json.dumps(fake_pkt_payload).encode('utf-8')
        fake_pkt = Ether() / IP() / UDP() / Raw(load=fake_pkt_payload_bin)

        cn_demo_1.process_packet(fake_pkt)

        assert cn_demo_1.packet_queue.empty()
    