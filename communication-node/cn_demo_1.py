import json
from scapy.all import *
import socket
import queue
import threading
import time
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SNIFF_INTERFACE_IN = os.getenv("SNIFF_INTERFACE_IN")
SNIFF_INTERFACE_OUT = os.getenv("SNIFF_INTERFACE_OUT")
OUT_INTERFACE = os.getenv("OUT_INTERFACE")
MY_MAC = os.getenv("MY_MAC")
MY_IP = os.getenv("MY_IP")
CNSS_IP = os.getenv("CNSS_IP")
TIME_WINDOW = os.getenv("TIME_WINDOW")

required_vars = {
    "SNIFF_INTERFACE_IN": SNIFF_INTERFACE_IN,
    "SNIFF_INTERFACE_OUT": SNIFF_INTERFACE_OUT,
    "OUT_INTERFACE": OUT_INTERFACE,
    "MY_MAC": MY_MAC,
    "MY_IP": MY_IP,
    "CNSS_IP": CNSS_IP,
    "TIME_WINDOW": TIME_WINDOW
}

for var_name, var_value in required_vars.items():
    if var_value is None:
        raise ValueError(f"Environment variable {var_name} is not set!")


packet_queue_in = queue.Queue()
packet_queue_out = queue.Queue()

sequence = 0
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def sending_data_to_cnss():
    global sequence
    while True:
        time.sleep(int(TIME_WINDOW))
        
        sequence += 1

        packets_to_send_in = []
        packets_to_send_out = []

        while not packet_queue_in.empty():
            packets_to_send_in.append(packet_queue_in.get_nowait())

        while not packet_queue_out.empty():
            packets_to_send_out.append(packet_queue_out.get_nowait())

        packet_to_cnss = {
             "channel_id": "main_tp_dev",
             "sequence": sequence,
             "window_ms": int(TIME_WINDOW) * 1000,
             "direction_out": {
               "packets": len(packets_to_send_out)
            },
             "direction_in": {
               "packets": len(packets_to_send_in)
            },
             "timestamp": datetime.now(timezone.utc).strftime(r'%Y-%m-%dT%H:%M:%SZ')
        }
  
        packet_to_cnss = json.dumps(packet_to_cnss).encode('utf-8')
        # packet_to_send = (
        #     Ether(src=MY_MAC)
        #     / IP(src=MY_IP, dst=CNSS_IP)
        #     / UDP(sport=5140, dport=5140)
        #     / Raw(load=packet_to_cnss)
        # )
        # sendp(packet_to_send, iface=OUT_INTERFACE, verbose=2)
        udp_socket.sendto(packet_to_cnss, (CNSS_IP, 5140))
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
    udp_socket.close()
