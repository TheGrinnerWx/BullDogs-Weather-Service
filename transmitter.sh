#!/bin/bash

# PERSISTENT TRANSMITTER (NO-DROP): BULLDOGS WEATHER RADIO (WXB26)
# This script maintains a 24/7 connection to Caster.fm with constant background hum.
# It mixes in the voice from the sequencer whenever available.

SERVER="sapircast.caster.fm"
PORT="14838"
PASSWORD="nycJx85Tcp"
MOUNT="/ymsoe"

echo "Starting No-Drop Persistent Transmitter (64kbps)..."

# CONFIGURATION:
# - Loop the background noise (KHB49-Noise.mp3) as the PRIMARY source.
# - Mix in the UDP input (Voice) with 1.8x gain for loud alerts.
# - Use basic metadata to ensure FFmpeg compatibility.

/opt/homebrew/bin/ffmpeg -hide_banner -loglevel warning \
  -stream_loop -1 -i KHB49-Noise.mp3 \
  -f s16le -ar 44100 -ac 1 -i "udp://127.0.0.1:9000?fifo_size=1000000&overrun_nonfatal=1" \
  -filter_complex "[0:a]volume=0.6[noise];[1:a]volume=1.8[voice];[noise][voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0" \
  -c:a libmp3lame -b:a 64k -ar 44100 -ac 2 \
  -metadata title="WXB26 Bulldogs Weather Radio" \
  -metadata artist="Metropolitan Weather Service" \
  -content_type 'audio/mpeg' \
  -f mp3 "icecast://source:$PASSWORD@$SERVER:$PORT$MOUNT"
