import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

os.environ["SNIFF_INTERFACE"] = "fake_eth"
os.environ["OUT_INTERFACE"] = "fake_eth1"
os.environ["MY_MAC"] = "12:34:56:78:90:ab"
os.environ["MY_IP"] = "192.168.100.2"
os.environ["TIME_WINDOW"] = "50"
