from scapy.all import Ether, IP, Raw, sendp, hexdump, get_if_hwaddr
import socket, time

flag = 0xDEADC0DE
new_ip = input("Print new IP address to block: ")
ip = list(map(int, new_ip.split(".")))

if all(0 < octet < 256 for octet in ip):
    ip_bytes = socket.inet_aton(new_ip)
    flag_bytes = flag.to_bytes(4, 'big')
    payload = flag_bytes + ip_bytes

    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / IP(dst="255.255.255.255") / Raw(load=payload)
    hexdump(pkt)

    sendp(pkt, iface="eth1", verbose=True)
else:
    print("Wrong IP address!")