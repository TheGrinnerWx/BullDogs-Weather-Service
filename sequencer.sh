#!/bin/bash

# SEQUENCED PLAYER: BULLDOGS WEATHER RADIO (WXB26)
# This script feeds the UDP transmitter with available audio files.
# It now plays files ONE-BY-ONE from the playlist only IF they exist.
# This prevents the station from being silent while the Brain is still generating.

echo "Starting Bulldogs Weather Radio Sequencer (Dynamic Playback)..."

while true; do
  # 1. PRIORITY INJECTION CHECK: 
  if [ -f "PRIORITY_INJECTION.wav" ]; then
    echo "🚨 PRIORITY INJECTION DETECTED!"
    /opt/homebrew/bin/ffmpeg -re -i "PRIORITY_INJECTION.wav" \
      -f s16le -ar 44100 -ac 1 "udp://127.0.0.1:9000?pkt_size=1316"
    rm "PRIORITY_INJECTION.wav"
  fi

  # 2. Guard: Ensure playlist.txt exists
  if [ ! -s "playlist.txt" ]; then
    sleep 2
    continue
  fi

  # 3. Dynamic Playback Loop:
  # Instead of 'concat' (which fails on missing files), we play individually.
  while read line; do
    # Extract the file path from 'file '/path/to/file.wav''
    FILE_PATH=$(echo "$line" | sed "s/^file '//;s/'$//")
    
    if [ -f "$FILE_PATH" ]; then
        echo "[SEQUENCER] Playing: $(basename "$FILE_PATH")"
        /opt/homebrew/bin/ffmpeg -re -i "$FILE_PATH" \
          -f s16le -ar 44100 -ac 1 "udp://127.0.0.1:9000?pkt_size=1316"
    else
        echo "[SEQUENCER] Skipping missing file: $(basename "$FILE_PATH")"
        # Don't wait too long, just skip to the next available one.
    fi

    # Check for priority alerts again mid-playlist for maximum response
    if [ -f "PRIORITY_INJECTION.wav" ]; then break; fi
    
  done < "playlist.txt"

  sleep 1
done
