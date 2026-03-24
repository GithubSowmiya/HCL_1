# Layer 3 - Highlight Detector
# Reads frame data from Layer 2, scores each frame using 3 signals,
# and prints FFmpeg commands to cut video clips for detected highlights.
#
# Run: python3 highlight_detector.py

import json
import os
import math

FRAMES_FILE   = "../data/frames.json"
OUTPUT_FOLDER = "../output"
THRESHOLD     = 0.50   # score >= 0.50 is a highlight
CLIP_BEFORE   = 3.0    # seconds before the event to include
CLIP_AFTER    = 5.0    # seconds after the event to include


# Ball-by-ball match data (timestamp, event, description)
# In production this comes from a live cricket API like Cricbuzz.
SCORECARD = [
    (0.4,  "dot",    "Good length, defended"),
    (1.6,  "single", "Nudged to midwicket"),
    (2.0,  "dot",    "Played and missed"),
    (2.2,  "four",   "Driven through covers!"),
    (2.8,  "dot",    "Short ball, ducked under"),
    (2.0,  "six",    "SIX! Rohit clears long-on!"),
    (4.0,  "wicket", "BOWLED! Off stump shattered!"),
    (6.0,  "six",    "SIX! Pulls it into the stands!"),
    (7.2,  "four",   "Late cut for four"),
]

EVENT_SCORES = {
    "six":    1.0,
    "wicket": 0.9,
    "four":   0.7,
    "two":    0.3,
    "single": 0.2,
    "dot":    0.1,
    "wide":   0.05,
}


def get_audio_score(frame, all_frames):
    crowd = frame["crowd"]
    frame_num = frame["frame"]

    # Collect crowd values from the 10 frames before this one
    recent = [f["crowd"] for f in all_frames
              if frame_num - 10 <= f["frame"] < frame_num]

    spike = 0.0
    if len(recent) >= 5:
        avg = sum(recent) / len(recent)
        jump = crowd - avg
        if jump > 0.3:
            spike = min(jump, 1.0) * 0.25

    return round(min(crowd * 0.40 + spike, 1.0), 3)


def get_video_score(frame, prev_frame):
    score = 0.0

    if frame["boundary"]:
        score += 0.40

    if prev_frame is not None:
        diff = abs(frame["brightness"] - prev_frame["brightness"])
        score += min(diff / 40.0, 1.0) * 0.35

    return round(min(score, 1.0), 3)


def get_scorecard_score(timestamp):
    best_score = 0.0
    best_desc  = "no event"

    for event_time, event_type, description in SCORECARD:
        if abs(event_time - timestamp) <= 0.5:
            s = EVENT_SCORES.get(event_type, 0.1)
            if s > best_score:
                best_score = s
                best_desc  = description

    return best_score, best_desc


def get_final_score(audio, video, scorecard):
    return round(min(audio * 0.30 + video * 0.30 + scorecard * 0.40, 1.0), 3)


def print_ffmpeg_command(clip_num, label, start, duration):
    out = os.path.join(OUTPUT_FOLDER, f"clip_{clip_num:02d}_{label}.mp4")
    print(f"\n  ffmpeg -ss {start:.1f} -i your_match.mp4 -t {duration:.1f} \\")
    print(f"    -vf \"drawtext=text='{label}':fontsize=48:fontcolor=white:x=10:y=10\" \\")
    print(f"    -c:v libx264 -c:a aac {out}")


def main():
    print("Layer 3: Highlight Detector started\n")

    # Load frames saved by Layer 2, or generate simulated data
    if os.path.exists(FRAMES_FILE):
        with open(FRAMES_FILE) as f:
            frames = json.load(f)
        print(f"Loaded {len(frames)} frames from {FRAMES_FILE}\n")
    else:
        print("No frames file found. Using simulated data.\n")
        frames = []
        for i in range(200):
            crowd = 0.10 + (i % 5) * 0.02
            if 48 <= i <= 55:   crowd = 0.95
            elif 98 <= i <= 105: crowd = 0.80
            elif 148 <= i <= 155: crowd = 0.90
            frames.append({
                "frame":      i,
                "time":       round(i / 25.0, 3),
                "brightness": round(150 + 50 * math.sin(i * 0.1), 2),
                "crowd":      round(crowd, 2),
                "boundary":   50 <= i <= 55
            })
        os.makedirs(os.path.dirname(FRAMES_FILE), exist_ok=True)
        with open(FRAMES_FILE, "w") as f:
            json.dump(frames, f, indent=2)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print(f"  {'Frame':>6} | {'Time':>5} | {'Audio':>6} | {'Video':>6} | {'Card':>5} | {'Score':>6}")
    print(f"  {'-'*6}   {'-'*5}   {'-'*6}   {'-'*6}   {'-'*5}   {'-'*6}")

    highlights = []
    last_highlight_time = -99.0
    clip_count = 0

    for i, frame in enumerate(frames):
        prev = frames[i - 1] if i > 0 else None

        audio     = get_audio_score(frame, frames)
        video     = get_video_score(frame, prev)
        card, desc = get_scorecard_score(frame["time"])
        score     = get_final_score(audio, video, card)

        if frame["frame"] % 25 == 0:
            print(f"  {frame['frame']:>6} | {frame['time']:>4.1f}s | "
                  f"{audio:>6.3f} | {video:>6.3f} | {card:>5.2f} | {score:>6.3f}")

        gap = frame["time"] - last_highlight_time
        if score >= THRESHOLD and gap >= 2.0:
            clip_count += 1
            last_highlight_time = frame["time"]

            if card >= 0.9:
                label = "SIX" if "SIX" in desc.upper() else "WICKET"
            elif card >= 0.7:
                label = "FOUR"
            else:
                label = "HIGHLIGHT"

            h = {
                "clip_num":    clip_count,
                "label":       label,
                "frame":       frame["frame"],
                "time":        frame["time"],
                "score":       score,
                "description": desc,
                "clip_start":  max(0, frame["time"] - CLIP_BEFORE),
                "clip_end":    frame["time"] + CLIP_AFTER,
            }
            highlights.append(h)

            print(f"\n  {'='*48}")
            print(f"  HIGHLIGHT #{clip_count}  [{label}]")
            print(f"  Frame {frame['frame']}  |  Time {frame['time']:.2f}s  |  Score {score:.3f}")
            print(f"  {desc}")
            print(f"  Clip: {h['clip_start']:.1f}s to {h['clip_end']:.1f}s")
            print(f"  {'='*48}\n")

    print(f"\nTotal frames : {len(frames)}")
    print(f"Highlights   : {len(highlights)}")

    if highlights:
        print("\nFFmpeg commands to cut the clips:")
        for h in highlights:
            print_ffmpeg_command(h["clip_num"], h["label"],
                                 h["clip_start"], h["clip_end"] - h["clip_start"])

    out_file = os.path.join(OUTPUT_FOLDER, "highlights.json")
    with open(out_file, "w") as f:
        json.dump(highlights, f, indent=2)

    print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    main()
