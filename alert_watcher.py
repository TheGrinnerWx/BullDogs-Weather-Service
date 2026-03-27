import os
import time
import json
import logging
import subprocess
import requests
from datetime import datetime
from utils import produce_wav_file, clean_weather_text
from EAS import encode_eas_to_wav, generate_same_header

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s')
logger = logging.getLogger("ALERT_WATCHER")

SEEN_ALERTS_FILE = "seen_alerts.json"

def load_seen_alerts():
    if os.path.exists(SEEN_ALERTS_FILE):
        try:
            with open(SEEN_ALERTS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen_alerts(seen_set):
    with open(SEEN_ALERTS_FILE, 'w') as f:
        json.dump(list(seen_set), f)

def get_priority_injection(event_code, alert_text, config, is_warning=True):
    """
    Builds the full sequence and saves it to PRIORITY_INJECTION.wav.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inject_wav = os.path.join(base_dir, "PRIORITY_INJECTION.wav")
    
    # EAS Components
    header_wav = os.path.join(base_dir, "bmh_wav", "alert_header.wav")
    attention_wav = os.path.join(base_dir, "bmh_wav", "alert_attention.wav")
    script_wav = os.path.join(base_dir, "bmh_wav", "alert_script.wav")
    eom_wav = os.path.join(base_dir, "bmh_wav", "alert_eom.wav")
    silence_wav = os.path.join(base_dir, "bmh_wav", "silence.wav")
    beep_wav = os.path.join(base_dir, "bmh_wav", "alert_beep.wav")
    
    sox_path = "/opt/homebrew/bin/sox"
    
    # Generate Alert Text
    logger.info("Synthesizing Alert Text...")
    cleaned_text = clean_weather_text(alert_text)
    produce_wav_file(cleaned_text, script_wav)
    
    if is_warning:
        # FULL EAS Sequence for Warnings
        eas_config = config.get('EAS', {})
        locations = eas_config.get('locations', ["036061"])
        org = eas_config.get('originator', "WXR")
        
        header_text = generate_same_header(org=org, eee=event_code, locations=locations, tttt="0030")
        logger.info("Encoding SAME Header: {}".format(header_text))
        encode_eas_to_wav(header_text, header_wav)
        
        logger.info("Generating 1050Hz Attention Tone...")
        subprocess.run([sox_path, "-n", "-r", "44100", "-c", "1", attention_wav, "synth", "8.0", "sine", "1050"], check=True)
        
        encode_eas_to_wav("NNNN", eom_wav)
        
        logger.info("Assembling EAS Injection...")
        combine_cmd = [
            sox_path,
            header_wav, silence_wav, header_wav, silence_wav, header_wav, silence_wav,
            attention_wav, script_wav, silence_wav,
            eom_wav, silence_wav, eom_wav, silence_wav, eom_wav,
            inject_wav
        ]
    else:
        # Smaller Intro for Advisories/Watches
        logger.info("Generating Advisory Intro Beeps...")
        subprocess.run([sox_path, "-n", "-r", "44100", "-c", "1", beep_wav, "synth", "0.5", "sine", "880", "synth", "0.5", "sine", "440"], check=True)
        
        logger.info("Assembling Advisory Injection...")
        combine_cmd = [
            sox_path,
            beep_wav, silence_wav, beep_wav, silence_wav,
            script_wav,
            inject_wav
        ]
        
    subprocess.run(combine_cmd, check=True)
    logger.info("🚨 ALERT READY: {}".format(inject_wav))

def poll_nws_alerts():
    logger.info("Starting NWS Real-Time Alert Watcher...")
    seen_alerts = load_seen_alerts()
    
    while True:
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            alert_zones = config['AlertSummary']['alertZones']
            priority_events = config.get('EAS', {}).get('priorityEvents', ["TOR", "SVR", "FFW", "SQW", "SMW"])
            
            for zone in alert_zones:
                url = "https://api.weather.gov/alerts/active/zone/{}".format(zone)
                response = requests.get(url, timeout=15)
                if response.status_code != 200: continue
                
                data = response.json()
                for feature in data.get('features', []):
                    alert_id = feature['id']
                    props = feature['properties']
                    
                    event = props.get('event')
                    event_code = "".join(props.get('parameters', {}).get('AWIPSidentifier', []))[0:3]
                    severity = props.get('severity')
                    
                    if alert_id not in seen_alerts:
                        # Priority Warning?
                        is_warning = (event_code in priority_events or severity in ['Extreme', 'Severe'])
                        
                        logger.info("!!! NEW ALERT DETECTED: {} ({}) !!!".format(event, event_code))
                        
                        full_text = "The National Weather Service has issued a {}. {}. {}".format(
                            event, props.get('description', ''), props.get('instruction', '')
                        )
                        
                        get_priority_injection(event_code, full_text, config, is_warning=is_warning)
                        
                        seen_alerts.add(alert_id)
                        save_seen_alerts(seen_alerts)
                        
                        while os.path.exists("PRIORITY_INJECTION.wav"):
                            time.sleep(2)
                        logger.info("Injection complete.")

        except Exception as e:
            logger.error("Polling error: {}".format(e))
            
        time.sleep(60)

if __name__ == "__main__":
    poll_nws_alerts()
