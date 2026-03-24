# Layer 2 - Transport
# Listens on UDP port 9000, receives frame data from Layer 1,
# parses it, and saves everything to a JSON file for Layer 3.
#
# Run: python3 transport.py
# (Start this before running the C program)

import socket
import json
import os

PORT       = 9000
SAVE_FILE  = "../data/frames.json"
MAX_FRAMES = 200


def parse_message(raw_text):
    # Input:  "FRAME:5|TIME:0.20|BRIGHT:148.2|CROWD:0.15|BOUNDARY:0"
    # Output: {"frame": 5, "time": 0.2, "brightness": 148.2, ...}
    frame_data = {}
    parts = raw_text.strip().split("|")

    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)

        if key == "FRAME":
            frame_data["frame"] = int(value)
        elif key == "TIME":
            frame_data["time"] = float(value)
        elif key == "BRIGHT":
            frame_data["brightness"] = float(value)
        elif key == "CROWD":
            frame_data["crowd"] = float(value)
        elif key == "BOUNDARY":
            frame_data["boundary"] = int(value) == 1

    return frame_data


def main():
    print("Layer 2: Transport receiver started")
    print(f"Listening on port {PORT}...\n")

    os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", PORT))
    sock.settimeout(3.0)

    all_frames = []
    frames_received = 0

    while frames_received < MAX_FRAMES:
        try:
            raw_data, sender = sock.recvfrom(1024)
            message = raw_data.decode("utf-8")
            frame_data = parse_message(message)
            all_frames.append(frame_data)
            frames_received += 1

            if frames_received % 25 == 0:
                print(f"[recv] {frames_received} frames  "
                      f"frame={frame_data['frame']}  "
                      f"crowd={frame_data['crowd']:.2f}")

        except socket.timeout:
            print("\nNo more data from Layer 1. Saving...")
            break

    with open(SAVE_FILE, "w") as f:
        json.dump(all_frames, f, indent=2)

    print(f"\nSaved {len(all_frames)} frames to {SAVE_FILE}")
    sock.close()


if __name__ == "__main__":
    main()
