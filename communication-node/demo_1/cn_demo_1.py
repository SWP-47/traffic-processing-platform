import json
from scapy.all import *
import queue
import threading
import time
import os
from dotenv import load_dotenv

load_dotenv()

SNIFF_INTERFACE_IN = os.getenv("SNIFF_INTERFACE_IN")
SNIFF_INTERFACE_OUT = os.getenv("SNIFF_INTERFACE_OUT")
OUT_INTERFACE = os.getenv("OUT_INTERFACE")
MY_MAC = os.getenv("MY_MAC")
MY_IP = os.getenv("MY_IP")
CNSS_IP = os.getenv("CNSS_IP")

required_vars = {
    "SNIFF_INTERFACE_IN": SNIFF_INTERFACE_IN,
    "SNIFF_INTERFACE_OUT": SNIFF_INTERFACE_OUT,
    "OUT_INTERFACE": OUT_INTERFACE,
    "MY_MAC": MY_MAC,
    "MY_IP": MY_IP,
    "CNSS_IP": CNSS_IP,
}

for var_name, var_value in required_vars.items():
    if var_value is None:
        raise ValueError(f"Environment variable {var_name} is not set!")


packet_queue_in = queue.Queue()
packet_queue_out = queue.Queue()


def sending_data_to_cnss():
    while True:
        time.sleep(0.5)

        if packet_queue_in.empty() and packet_queue_out.empty():
            continue

        packets_to_send_in = []
        packets_to_send_out = []

        if not packet_queue_in.empty():
            while not packet_queue_in.empty():
                packets_to_send_in.append(packet_queue_in.get_nowait())

        if not packet_queue_out.empty():
            while not packet_queue_out.empty():
                packets_to_send_out.append(packet_queue_out.get_nowait())

        packet_to_cnss = {
            "timestamp": int(time.time() * 1000),
            "packets_in": len(packets_to_send_in),
            "packets_out": len(packets_to_send_out),
        }

        packet_to_cnss = json.dumps(packet_to_cnss)
        packet_to_send = (
            Ether(src=MY_MAC, dst="ff:ff:ff:ff:ff:ff")
            / IP(src=MY_IP, dst=CNSS_IP)
            / UDP(sport=80, dport=80)
            / Raw(load=packet_to_cnss)
        )
        sendp(packet_to_send, iface=OUT_INTERFACE, verbose=2)
        print("PACKET WAS SENT")


def process_packet_in(pkt):
    print(
        "------Packet captured------\n\n",
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

            packet_queue_in.put(parsed_json)

        except json.JSONDecodeError:
            return


def process_packet_out(pkt):
    print(
        "------Packet captured------\n\n",
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

            packet_queue_out.put(parsed_json)

        except json.JSONDecodeError:
            return


threading.Thread(target=sending_data_to_cnss, daemon=True).start()

sniffer_in = threading.Thread(
    target=lambda: sniff(
        iface=SNIFF_INTERFACE_IN, prn=process_packet_in, store=False
    ),
    daemon=True,
)
sniffer_out = threading.Thread(
    target=lambda: sniff(
        iface=SNIFF_INTERFACE_OUT, prn=process_packet_out, store=False
    ),
    daemon=True,
)

sniffer_in.start()
sniffer_out.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n Keyboard interruption")
