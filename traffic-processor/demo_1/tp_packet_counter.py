from scapy.all import *
import json
import os
from dotenv import load_dotenv

load_dotenv()

SNIFF_INTERFACE = os.getenv("SNIFF_INTERFACE_2")
OUT_INTERFACE = os.getenv("OUT_INTERFACE")
MY_MAC = os.getenv("MY_MAC_2")
MY_IP = os.getenv("MY_IP_2")
CN_IP = os.getenv("CN_IP")


def process_packet(pkt):
    if pkt[Ether].src == MY_MAC:
        return
    out_packet_payload = dict()
    out_packet_payload["size"] = len(pkt)
    out_packet_payload["srcMAC"] = pkt[Ether].src
    out_packet_payload["dstMAC"] = pkt[Ether].dst
    if IP in pkt:
        out_packet_payload["srcIP"] = pkt[IP].src
        out_packet_payload["dstIP"] = pkt[IP].dst
        if pkt[IP].payload and pkt[IP].payload.name != "Raw":
            out_packet_payload["L5proto"] = pkt[IP].payload.name
            if TCP in pkt:
                out_packet_payload["L6proto"] = pkt[TCP].payload.name
            elif UDP in pkt:
                out_packet_payload["L6proto"] = pkt[UDP].payload.name

    out_packet_payload = json.dumps(out_packet_payload)
    packet_to_send = (
        Ether(src=MY_MAC)
        / IP(src=MY_IP, dst=CN_IP)
        / UDP(sport=80, dport=80)
        / Raw(load=out_packet_payload)
    )
    sendp(packet_to_send, iface=OUT_INTERFACE, verbose=2)
    print(
        "------Packet captured------\n",
        out_packet_payload,
        "\n",
        pkt.summary(),
        "\n\n\n",
    )


sniff(iface=SNIFF_INTERFACE, prn=lambda pkt: process_packet(pkt), store=False)
