import json
from scapy.all import Raw, sniff
import socket
import queue
import threading
import time
import os
from dotenv import load_dotenv
from jsonschema import validate
from jsonschema.exceptions import ValidationError

load_dotenv()

SNIFF_INTERFACE = os.getenv("SNIFF_INTERFACE")
OUT_INTERFACE = os.getenv("OUT_INTERFACE")
MY_MAC = os.getenv("MY_MAC")
MY_IP = os.getenv("MY_IP")
CNSS_IP = os.getenv("CNSS_IP")
TIME_WINDOW = os.getenv("TIME_WINDOW")
CHANNEL_ID = os.getenv("CHANNEL_ID")

required_vars = {
    "SNIFF_INTERFACE_IN": SNIFF_INTERFACE,
    "OUT_INTERFACE": OUT_INTERFACE,
    "MY_MAC": MY_MAC,
    "MY_IP": MY_IP,
    "CNSS_IP": CNSS_IP,
    "TIME_WINDOW": TIME_WINDOW,
    "CHANNEL_ID": CHANNEL_ID,
}

for var_name, var_value in required_vars.items():
    if var_value is None:
        raise ValueError(f"Environment variable {var_name} is not set!")
    if var_name == "TIME_WINDOW" and int(var_value) > 60:
        raise ValueError(
            f"Please set the time window less than 60 ms to avoid \
            fragmentation problems! Your current time window: {var_value}"
        )


packet_queue = queue.Queue()

sequence = 0
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    udp_socket.setsockopt(
        socket.SOL_SOCKET, socket.SO_BINDTODEVICE, OUT_INTERFACE.encode()
    )
    print(f"Socket bound to interface: {OUT_INTERFACE}")
except (AttributeError, OSError) as e:
    print(f"Warning: Could not bind socket to {OUT_INTERFACE}: {e}")
    print("Socket will use OS routing table to choose interface")

json_from_tp_schema = {
    "type": "object",
    "properties": {
        "direction": {"type": "integer", "minimum": 0, "maximum": 1},
        "src_ip": {"type": ["string", "null"]},
        "dst_ip": {"type": ["string", "null"]},
        "src_port": {"type": ["integer", "null"]},
        "dst_port": {"type": ["integer", "null"]},
    },
    "required": ["direction", "src_ip", "dst_ip", "src_port", "dst_port"],
}


def make_json_for_cnss(packets_to_send, sequence):
    packet_to_cnss = {
        "channel_id": CHANNEL_ID,
        "timestamp": int(time.time()),
        "sequence": sequence,
        "window_ms": int(TIME_WINDOW),
        "packets": packets_to_send,
    }
    return packet_to_cnss


def sending_data_to_cnss():
    global sequence
    while True:
        time.sleep(int(TIME_WINDOW) / 1000.0)

        packets_to_send = []

        while not packet_queue.empty():
            packets_to_send.append(packet_queue.get_nowait())

        if len(packets_to_send) > 0:
            sequence += 1
            packet_to_cnss = make_json_for_cnss(packets_to_send, sequence)
            packet_to_cnss = json.dumps(packet_to_cnss).encode("utf-8")
            udp_socket.sendto(packet_to_cnss, (CNSS_IP, 5140))
            print(f"PACKET WAS SENT, sequence: {sequence}")


def process_packet(pkt):
    if Raw in pkt:
        try:
            raw_data = pkt[Raw].load.decode("utf-8", errors="ignore")
            parsed_json = json.loads(raw_data)
            try:
                validate(instance=parsed_json, schema=json_from_tp_schema)
            except ValidationError:
                return
            print(parsed_json)

            packet_queue.put(parsed_json)

        except json.JSONDecodeError:
            return


if __name__ == "__main__":
    threading.Thread(target=sending_data_to_cnss, daemon=True).start()

    sniffer = threading.Thread(
        target=lambda: sniff(
            iface=SNIFF_INTERFACE, prn=process_packet, store=False
        ),
        daemon=True,
    )

    sniffer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n Keyboard interruption")
        udp_socket.close()
