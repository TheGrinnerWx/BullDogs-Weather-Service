import os
import shutil
import subprocess
import logging
from flask import Flask, render_template, request, jsonify
from EAS import generate_same_header, encode_eas_to_wav
import utils

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ControlPanel")

app = Flask(__name__)

BASE_DIR = "/Users/leobernstein/weather-radio-suite"
WAV_DIR = os.path.join(BASE_DIR, "bmh_wav")
PRIORITY_FILE = os.path.join(BASE_DIR, "PRIORITY_INJECTION.wav")

# Presets
EVENT_CODES = {
    "RWT": "Required Weekly Test",
    "TOR": "Tornado Warning",
    "SVR": "Severe Thunderstorm Warning",
    "FFW": "Flash Flood Warning",
    "SQW": "Snow Squall Warning",
    "SMW": "Special Marine Warning",
    "EVI": "Evacuation Immediate",
    "CEM": "Civil Emergency Message",
    "ADR": "Administrative Message"
}

FIPS_NYC = [
    ("036061", "New York (Manhattan)"),
    ("036005", "Bronx"),
    ("036047", "Kings (Brooklyn)"),
    ("036081", "Queens"),
    ("036085", "Richmond (Staten Island)"),
    ("034013", "Essex, NJ"),
    ("034017", "Hudson, NJ"),
    ("034031", "Passaic, NJ")
]

@app.route('/')
def index():
    return render_template('index.html', event_codes=EVENT_CODES, locations=FIPS_NYC)

@app.route('/trigger', methods=['POST'])
def trigger():
    try:
        data = request.json
        eee = data.get('event_code', 'RWT')
        locs = data.get('locations', ['036061'])
        script = data.get('script', "This is a test of the Emergency Alert System.")
        org = data.get('originator', 'WXR')
        
        # Load purge time from config
        config = utils.load_config()
        eas_config = config.get("EAS", {})
        purge_map = eas_config.get("purgeTimeMap", {})
        tttt = purge_map.get(eee, eas_config.get("purgeTime", "0015"))
        
        log.info(f"Manual Alert Triggered: {eee} for {locs} with purge {tttt}")
        
        # 1. Generate SAME Header (3 times)
        # We no longer pass timestamp, generate_same_header() will calculate JJJHHMM UTC
        header_text = generate_same_header(org=org, eee=eee, locations=locs, tttt=tttt)
        header_wav = os.path.join(WAV_DIR, "manual_header.wav")
        encode_eas_to_wav(header_text, header_wav)
        
        # 2. Generate 1050Hz Attention Tone (8 seconds)
        tone_wav = os.path.join(WAV_DIR, "manual_tone.wav")
        sox_bin = shutil.which('sox') or '/opt/homebrew/bin/sox'
        subprocess.run([sox_bin, '-n', '-r', '44100', '-c', '1', tone_wav, 'synth', '8', 'sine', '1050'], check=True)
        
        # 3. Generate TTS Script
        script_wav = os.path.join(WAV_DIR, "manual_script.wav")
        utils.produce_wav_file(script, script_wav)
        
        # 4. Generate EOM Tones (3 times)
        eom_wav = os.path.join(WAV_DIR, "manual_eom.wav")
        encode_eas_to_wav("NNNN", eom_wav)
        
        # 5. Combine with NWS standard repeats
        # Format: [Header] x3 -> 1s pause -> Tone -> Script -> [EOM] x3
        final_manual = os.path.join(WAV_DIR, "MANUAL_ALERT.wav")
        
        # Build the SoX command
        # We use a 1s silence between header and tone
        silence_wav = os.path.join(WAV_DIR, "silence_1s.wav")
        subprocess.run([sox_bin, '-n', '-r', '44100', '-c', '1', silence_wav, 'trim', '0', '1'], check=True)
        
        combine_cmd = [
            sox_bin,
            header_wav, header_wav, header_wav,
            silence_wav,
            tone_wav,
            script_wav,
            eom_wav, eom_wav, eom_wav,
            final_manual
        ]
        subprocess.run(combine_cmd, check=True)
        
        # 6. Inject!
        shutil.copy(final_manual, PRIORITY_FILE)
        
        return jsonify({"status": "success", "message": f"Alert {eee} injected successfully!"})
        
    except Exception as e:
        log.error(f"Alert Injection Failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Running on port 8080 by default
    app.run(host='0.0.0.0', port=8080, debug=True)
