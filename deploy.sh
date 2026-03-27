#!/bin/bash

# Deployment script for Bulldogs Weather Radio (WXB26)
# Remote: Oracle Cloud Instance (opc@129.80.41.223)

REMOTE_USER="opc"
REMOTE_HOST="129.80.41.223"
REMOTE_PATH="~/weather-radio-suite"
SSH_KEY="~/Downloads/ssh-key-2026-02-24.key"

echo "🚀 Syncing stable weather radio suite to Oracle Cloud..."

# Sync everything except large media, virtualenvs, and local logs
rsync -avz -e "ssh -i $SSH_KEY" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.pm2' \
    --exclude 'bmh_wav/*.wav' \
    --exclude 'FINAL_CYCLE.wav' \
    --exclude 'CurrentTime.wav' \
    --exclude 'StationID.wav' \
    --exclude 'Forecast.wav' \
    --exclude 'venv' \
    --exclude '.gemini' \
    --exclude 'logs' \
    ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/

echo "✅ Sync complete!"
echo "To restart on remote, run: ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_PATH && pm2 restart all'"
