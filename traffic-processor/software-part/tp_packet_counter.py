from scapy.all import *
import json
import os
from dotenv import load_dotenv

load_dotenv()

SNIFF_INTERFACE_IN = os.getenv("SNIFF_INTERFACE_IN")
SNIFF_INTERFACE_OUT = os.getenv("SNIFF_INTERFACE_OUT")
OUT_INTERFACE = os.getenv("OUT_INTERFACE")
MY_MAC = os.getenv("MY_MAC")
MY_IP = os.getenv("MY_IP")
CN_IP = os.getenv("CN_IP")

required_vars = {
    "SNIFF_INTERFACE_IN": SNIFF_INTERFACE_IN,
    "SNIFF_INTERFACE_OUT": SNIFF_INTERFACE_OUT,
    "OUT_INTERFACE": OUT_INTERFACE,
    "MY_MAC": MY_MAC,
    "MY_IP": MY_IP,
    "CN_IP": CN_IP
}

for var_name, var_value in required_vars.items():
    if var_value is None:
        raise ValueError(f"Environment variable {var_name} is not set!")

packet_queue_in = queue.Queue()
packet_queue_out = queue.Queue()

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def get_json_payload(pkt, direction):
    src_ip = 0
    dst_ip = 0
    src_port = 0
    dst_port = 0

    if IP in pkt:
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        try:
            src_port = pkt[IP].payload.sport
            dst_port = pkt[IP].payload.dport
        except AttributeError:
            src_port = None
            dst_port = None
    else:
        src_ip = None
        dst_ip = None
        src_port = None
        dst_port = None
    
    json_payload = {
        "direction": direction,   
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
    }
    return json_payload

def sending_data_to_cnss():
    while True:
        try:
            if not packet_queue_in.empty():
                packet_to_cn = packet_queue_in.get_nowait()
                packet_to_cn = json.dumps(packet_to_cn).encode('utf-8')
                udp_socket.sendto(packet_to_cn, (CN_IP, 5140))
                print("PACKET WAS SENT")

            if not packet_queue_out.empty():
                packet_to_cn = packet_queue_out.get_nowait()
                packet_to_cn = json.dumps(packet_to_cn).encode('utf-8')
                udp_socket.sendto(packet_to_cn, (CN_IP, 5140))
                print("PACKET WAS SENT")

            time.sleep(0.3)
        except queue.Empty:
            pass 
        except Exception as e:
            print(f"ERROR whyle sending packets to CN\n {e}")
            time.sleep(1) 

def process_packet_in(pkt):
    # src_ip = 0
    # dst_ip = 0
    # src_port = 0
    # dst_port = 0

    # if IP in pkt:
    #     src_ip = pkt[IP].src
    #     dst_ip = pkt[IP].dst
    #     try:
    #         src_port = pkt[IP].payload.sport
    #         dst_port = pkt[IP].payload.dport
    #     except AttributeError:
    #         src_port = None
    #         dst_port = None
    # else:
    #     src_ip = None
    #     dst_ip = None
    #     src_port = None
    #     dst_port = None
    
    # json_payload = {
    #     "direction": 0,   
    #     "src_ip": src_ip,
    #     "dst_ip": dst_ip,
    #     "src_port": src_port,
    #     "dst_port": dst_port,
    # }
    json_payload = get_json_payload(pkt, 0)
    packet_queue_in.put(json_payload)



def process_packet_out(pkt):
    # src_ip = 0
    # dst_ip = 0
    # src_port = 0
    # dst_port = 0

    # if IP in pkt:
    #     src_ip = pkt[IP].src
    #     dst_ip = pkt[IP].dst
    #     try:
    #         src_port = pkt[IP].payload.sport
    #         dst_port = pkt[IP].payload.dport
    #     except AttributeError:
    #         src_port = None
    #         dst_port = None
    # else:
    #     src_ip = None
    #     dst_ip = None
    #     src_port = None
    #     dst_port = None
    
    # json_payload = {
    #     "direction": 1,   
    #     "src_ip": src_ip,
    #     "dst_ip": dst_ip,
    #     "src_port": src_port,
    #     "dst_port": dst_port,
    # }
    json_payload = get_json_payload(pkt, 1)
    packet_queue_out.put(json_payload)

if __name__ == "__main__":
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

