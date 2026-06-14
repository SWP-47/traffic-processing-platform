import json
from scapy.all import *
import queue
import threading
import time
import os
from dotenv import load_dotenv

load_dotenv()

global SNIFF_INTERFACE
global OUT_INTERFACE
global MY_MAC

SNIFF_INTERFACE = os.getenv("SNIFF_INTERFACE_3")
OUT_INTERFACE = os.getenv("OUT_INTERFACE_3")
MY_MAC = os.getenv("MY_MAC_3")
MY_IP = os.getenv("MY_IP_3")
CNSS_IP = os.getenv("CNSS_IP")


packet_queue = queue.Queue()


def sending_data_to_cnss():
    while True:
        time.sleep(0.5)

        if packet_queue.empty():
            continue

        packets_to_send = []
        while not packet_queue.empty():
            packets_to_send.append(packet_queue.get_nowait())

        packet_to_cnss = dict()
        packet_to_cnss["timestamp"] = int(time.time() * 1000)
        packet_to_cnss["packets"] = packets_to_send

        packet_to_cnss = json.dumps(packet_to_cnss)
        packet_to_send = (
            Ether(src=MY_MAC, dst="ff:ff:ff:ff:ff:ff")
            / IP(src=MY_IP, dst=CNSS_IP)
            / UDP(sport=80, dport=80)
            / Raw(load=packet_to_cnss)
        )
        sendp(packet_to_send, iface=OUT_INTERFACE, verbose=2)
        print("PACKET WAS SENT")


threading.Thread(target=sending_data_to_cnss, daemon=True).start()


def process_packet(pkt):
    print(
        "------Packet captured------\n",
        "\n",
        pkt.summary(),
        "\n",
        pkt.payload,
        "\n\n\n",
    )
    if Raw in pkt:
        try:
            raw_data = pkt[Raw].load.decode("utf-8", errors="ignore")
            parsed_json = json.loads(raw_data)
            print(parsed_json)

            packet_queue.put(parsed_json)

        except json.JSONDecodeError:
            return


sniff(iface=SNIFF_INTERFACE, prn=lambda pkt: process_packet(pkt), store=False)
