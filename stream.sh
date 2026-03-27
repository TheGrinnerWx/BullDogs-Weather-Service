#!/bin/bash

SERVER="sapircast.caster.fm"
PORT="14838"
PASSWORD="nycJx85Tcp"
MOUNT="/ymsoe"

echo "Starting Bulldogs Weather Radio HIGH-PERSISTENCE Stream (64kbps)..."

while true; do
  # 1. PRIORITY INJECTION CHECK: 
  # If a priority file exists, play it IMMEDIATELY before the playlist.
  if [ -f "PRIORITY_INJECTION.wav" ]; then
    echo "🚨 PRIORITY INJECTION DETECTED! Broadcasting now..."
    /opt/homebrew/bin/ffmpeg -re -i "PRIORITY_INJECTION.wav" \
      -stream_loop -1 -i KHB49-Noise.mp3 \
      -filter_complex "[0:a]volume=1.2[v];[1:a]volume=0.7[n];[v][n]amix=inputs=2:duration=first" \
      -c:a libmp3lame -b:a 64k -ar 44100 -ac 2 \
      -metadata title="WXB26 EMERGENCY BROADCAST" \
      -content_type 'audio/mpeg' \
      -f mp3 icecast://source:$PASSWORD@$SERVER:$PORT$MOUNT
      
    rm "PRIORITY_INJECTION.wav"
    echo "✅ Priority injection complete. Returning to weather cycle..."
  fi

  # 2. Guard: Ensure playlist.txt exists and is not empty
  if [ ! -s "playlist.txt" ]; then
    echo "[STREAM] Waiting for live playlist from Brain..."
    sleep 10
    continue
  fi

  # 3. Guard: Ensure all files referenced in playlist exist
  MISSING_FILE=0
  while read p; do
    FILE_PATH=$(echo "$p" | sed "s/^file '//;s/'$//")
    if [ ! -f "$FILE_PATH" ]; then
      echo "[STREAM] Waiting for asset: $FILE_PATH"
      MISSING_FILE=1
      break
    fi
  done < "playlist.txt"

  if [ $MISSING_FILE -eq 1 ]; then
    sleep 5
    continue
  fi

  # 4. Normal Stream: Read the playlist, mix background noise (0.7x) and voice (1.2x)
  /opt/homebrew/bin/ffmpeg -re -f concat -safe 0 -i playlist.txt \
    -stream_loop -1 -i KHB49-Noise.mp3 \
    -filter_complex "[0:a]volume=1.2[v];[1:a]volume=0.7[n];[v][n]amix=inputs=2:duration=first" \
    -c:a libmp3lame -b:a 64k -ar 44100 -ac 2 \
    -metadata title="WXB26 Bulldogs Weather Radio" \
    -metadata artist="Bulldogs Weather Service" \
    -content_type 'audio/mpeg' \
    -maxrate 64k -bufsize 128k \
    -f mp3 icecast://source:$PASSWORD@$SERVER:$PORT$MOUNT
    
  echo "[STREAM] Stream cycle ended. Restarting in 5 seconds..."
  sleep 5
done
