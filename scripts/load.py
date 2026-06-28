import socket
import json
import time
import random
import threading


UDP_IP = "10.93.26.186"
UDP_PORT = 5140

CHANNELS = [
    "bridge-berlin-01",
    "bridge-prague-01",
    "bridge-warsaw-01",
]

# Режимы: чередуются каждые PHASE_SEC секунд
PHASE_SEC = 3
RATE_LOW = 100     # пакетов/сек
RATE_HIGH = 1000   # пакетов/сек

# ============================================================
# Глобальное состояние режима (общее для всех каналов)
# ============================================================
phase_lock = threading.Lock()
current_rate = RATE_LOW
phase_start = time.time()


def get_current_rate():
    """Возвращает целевую скорость, переключаясь каждые PHASE_SEC секунд."""
    global current_rate, phase_start
    now = time.time()
    with phase_lock:
        if now - phase_start >= PHASE_SEC:
            current_rate = RATE_HIGH if current_rate == RATE_LOW else RATE_LOW
            phase_start = now
        return current_rate


def random_packet():
    return {
        "direction": random.choice([0, 1]),
        "src_ip": f"192.168.1.{random.randint(1, 254)}",
        "dst_ip": f"8.8.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([53, 80, 443]),
    }


def build_batch(channel_id: str, sequence: int, packets: list) -> bytes:
    payload = {
        "channel_id": channel_id,
        "sequence": sequence,
        "window_ms": 100,
        "timestamp": int(time.time()),
        "packets": packets,
    }
    return json.dumps(payload).encode("utf-8")


def channel_worker(channel_id: str):
    """
    Поток для одного канала.
    Стратегия отправки:
      - Базовый тик = 10 мс (100 батчей/сек)
      - При RATE_HIGH (1000 п/с): 10 пакетов в батче  -> 100 * 10 = 1000 п/с
      - При RATE_LOW  (100 п/с):  1 пакет в батче каждые 10 мс -> 100 п/с
    Такой подход гарантирует, что размер UDP-датаграммы всегда < 1400 байт (MTU).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sequence = 1
    tick_sec = 0.010  # 10 мс

    print(f"[{channel_id}] worker started")

    while True:
        rate = get_current_rate()

        # Количество пакетов в одном батче зависит от режима
        packets_per_batch = 10 if rate == RATE_HIGH else 1

        packets = [random_packet() for _ in range(packets_per_batch)]
        msg = build_batch(channel_id, sequence, packets)

        # Защита от превышения MTU (на всякий случай)
        if len(msg) >= 1400:
            # Разрежем пакет на несколько батчей поменьше
            # Но при 10 пакетах это почти невозможно — оставим как есть
            pass

        try:
            sock.sendto(msg, (UDP_IP, UDP_PORT))
        except OSError as e:
            print(f"[{channel_id}] send error: {e}")

        sequence += 1
        time.sleep(tick_sec)


def monitor():
    """Печатает текущий режим раз в секунду."""
    while True:
        rate = get_current_rate()
        label = "HIGH (1000 pkt/s)" if rate == RATE_HIGH else "LOW  (100 pkt/s)"
        print(f"[monitor] {label}  |  channels: {CHANNELS}")
        time.sleep(1)


# ============================================================
# Запуск
# ============================================================
if __name__ == "__main__":
    threads = []
    for ch in CHANNELS:
        t = threading.Thread(target=channel_worker, args=(ch,), daemon=True)
        t.start()
        threads.append(t)

    mon = threading.Thread(target=monitor, daemon=True)
    mon.start()

    print("Press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")