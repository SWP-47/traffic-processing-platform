from scapy.all import *  
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Each packet contains: [Optionaly] size, src_mac, dest_mac, ethertype
# If IPv4: src_ip, dest_ip, [Optionaly] L4_proto(TCP, UDP...)
# [Optionaly] L5 proto (for TCP and UDP only)

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
    if (IP in pkt):
        out_packet_payload["srcIP"] = pkt[IP].src
        out_packet_payload["dstIP"] = pkt[IP].dst
        if pkt[IP].payload and pkt[IP].payload.name != "Raw":
            out_packet_payload["L5proto"] = pkt[IP].payload.name
            if TCP in pkt: 
                out_packet_payload["L6proto"] = pkt[TCP].payload.name
            elif UDP in pkt: 
                out_packet_payload["L6proto"] = pkt[UDP].payload.name

# dst="ff:ff:ff:ff:ff:ff"
    out_packet_payload = json.dumps(out_packet_payload)
    packet_to_send = Ether(src=MY_MAC) / IP(src=MY_IP, dst=CN_IP) / UDP(sport=80, dport=80) / Raw(load=out_packet_payload)
    sendp(packet_to_send, iface=OUT_INTERFACE, verbose=2)
    print("------Packet captured------\n", out_packet_payload, "\n", pkt.summary(), "\n\n\n")



sniff(iface=SNIFF_INTERFACE,
      prn=lambda pkt: process_packet(pkt),
      store=False)


# packet_to_send = Ether(src="98:5f:41:d8:be:b8") / IP(src ="10.91.89.55", dst="10.91.90.17") / Raw("))))))");
# sendp(packet_to_send, iface=INTERFACE, verbose=1);