#!/bin/bash

# EMERGENCY BROADCAST INJECTION: BULLDOGS WEATHER RADIO (WXB26)
echo "🚨 TRIGGERING EMERGENCY REQUIRED WEEKLY TEST..."

# Correct directory context
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. Generate the RWT Audio Sequence (SAME Header x3, Attn, Script, EOM x3)
echo "🛠 Generating EAS Tones and Script..."
./venv/bin/python RWT.py

# 2. Inject it as a PRIORITY INJECTION
if [ -f "bmh_wav/RWT.wav" ]; then
    echo "📋 Injecting RWT into priority buffer..."
    cp "bmh_wav/RWT.wav" "PRIORITY_INJECTION.wav"
    
    # 3. SURGICAL RESTART: 
    # We ONLY restart the sequencer. 
    # The 'wxb26-brain' and 'wxb26-transmitter' stay online. 
    # This prevents the Brain from resetting its 8-minute weather cycle.
    echo "📡 Switching Sequencer to Emergency Alert (SURGICAL RELAY)..."
    PATH="/usr/local/bin:$PATH" pm2 restart wxb26-sequencer
    
    echo "✅ SUCCESS: The test is now broadcasting live on your station!"
else
    echo "❌ ERROR: Failed to generate RWT audio. Check RWT.py logs."
    exit 1
fi
