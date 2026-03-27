#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
BMH Emulation Main Script

This script emulates the behavior of the NWS Broadcast Message Handler (BMH) system
by periodically generating various weather-related audio products and combining
them into a final audio output. The script runs in an infinite loop, updating
the audio files every minute (for time-only updates), with a full refresh cycle
every 10 minutes.
"""

# System-level imports
import os
import sys
import json
import time
from datetime import datetime
import shutil
import logging
import argparse
import tempfile
import traceback
import subprocess
from products import PRODUCT_GENERATORS
from current_time import getCurrentTime
from StationID import getStationID
from RWT import getRWT

# ... (logging setup)
class ColorFormatter(logging.Formatter):
    grey = "\x1b[90m"
    green = "\x1b[92m"
    yellow = "\x1b[93m"
    red = "\x1b[91m"
    reset = "\x1b[0m"

    format_str = "%(asctime)s | %(levelname)-8s | %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging(verbose, config_loglevel=None):
    try:
        loglevel = config_loglevel.upper() if config_loglevel else ('DEBUG' if verbose else 'INFO')
        log = logging.getLogger("BMH")
        log.setLevel(loglevel)

        if not log.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(loglevel)
            ch.setFormatter(ColorFormatter())
            log.addHandler(ch)
        return log
    except Exception:
        print(f"Error setting up logging: {traceback.format_exc()}")
        sys.exit(1)

last_station_id_time = 0
last_rwt_date = None

def refresh_products(log):
    for generator in PRODUCT_GENERATORS:
        log.info(f"[BMH] Executing generator: {generator.__name__}")
        try:
            generator()
        except Exception as e:
            log.error(f"[BMH] Error in generator {generator.__name__}: {e}")
            log.error(traceback.format_exc())

def combine_audio(AUDIO_SEQUENCE, log):
    path_separator = '\\' if os.name == 'nt' else '/'
    sox_location = shutil.which(f'binary{path_separator}sox.exe') if os.name == 'nt' else shutil.which('sox')
    if not sox_location:
        log.error("[BMH] SoX not found! Cannot combine audio.")
        return
        
    valid_sequence = [f for f in AUDIO_SEQUENCE if os.path.exists(f)]
    if not valid_sequence:
        log.warning("[BMH] No audio files to combine.")
        return

    # Use a temporary file in the SAME directory to ensure atomic os.replace works
    target_final = os.path.join(os.getcwd(), 'FINAL_CYCLE.wav')
    temp_final = os.path.join(os.getcwd(), 'FINAL_CYCLE_TEMP.wav')

    try:
        log.info(f"[BMH] Combining voice sequence into {temp_final}...")
        
        # 1. Concatenate the voice files into temp_final
        subprocess.run([sox_location, '-q'] + valid_sequence + [temp_final], check=True)
        
        # 2. Check for background noise and mix if present
        bg_noise = os.path.join(os.getcwd(), 'KHB49-Noise.mp3')
        if os.path.exists(bg_noise):
            log.info(f"[BMH] Mixing background noise: KHB49-Noise.mp3")
            voice_only = os.path.join(os.getcwd(), 'VOICE_ONLY_STAGE.wav')
            os.rename(temp_final, voice_only)
            
            try:
                # Use FFmpeg with amerge + pan for a "true" mix without the attenuation amix imposes
                ffmpeg_bin = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
                soxi_bin = shutil.which('soxi') or '/opt/homebrew/bin/soxi'
                
                # We need the exact duration to truncate the looped background noise correctly
                voice_dur = float(subprocess.check_output([soxi_bin, '-D', voice_only]).strip())
                
                # Formula: merge inputs, then sum them with 0.5x gain on the background (channel 1)
                # We use 0.5x to ensure it provides atmospheric static without drowning out the voice.
                mix_cmd = [
                    ffmpeg_bin, '-y', '-i', voice_only,
                    '-stream_loop', '-1', '-i', bg_noise,
                    '-filter_complex', '[0:a][1:a]amerge=inputs=2,pan=mono|c0=c0+0.5*c1[a]',
                    '-map', '[a]', '-t', str(voice_dur),
                    temp_final
                ]
                log.debug(f"[BMH] FFmpeg High-Gain Mix command: {' '.join(mix_cmd)}")
                subprocess.run(mix_cmd, check=True)
                
                if os.path.exists(voice_only):
                    os.remove(voice_only)
            except Exception as e:
                log.error(f"[BMH] High-gain mix failed: {e}")
                if os.path.exists(voice_only):
                    os.rename(voice_only, temp_final)

        # 3. Atomically replace the final broadcast file
        os.replace(temp_final, target_final)
        log.info(f"[BMH] Final combined audio with background noise saved to {os.path.basename(target_final)}")
    except Exception as e:
        log.error(f"[BMH] Error combining audio with SoX: {e}")
        log.error(traceback.format_exc())
    finally:
        if os.path.exists(temp_final):
            os.remove(temp_final)

def main(log, config):
    global last_station_id_time
    try:
        log.info('[BMH] Setting up BMH Emulation environment...')
        os.makedirs(os.path.join(os.getcwd(), 'bmh_wav'), exist_ok=True)
        
        for f in os.listdir('bmh_wav'):
            if f.endswith('.wav'):
                os.remove(os.path.join('bmh_wav', f))
        
        log.info('[BMH] Starting 8-Minute Cycle BMH Emulation. Hit Ctrl+C to stop.')
        
        while True:
            start_time = time.time()
            path_sep = '\\' if os.name == 'nt' else '/'
            
            refresh_products(log)
            
            AUDIO_SEQUENCE = []
            
            # Inject Station ID with current time at the START of EVERY cycle
            log.info("[BMH] Injecting Station ID and Current Time...")
            # Generate current time audio
            getCurrentTime()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}CurrentTime.wav')
            # Then generate station ID
            getStationID()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}StationID.wav')
            
            # Build sequence with frequent clock updates
            if not os.path.exists('NoAlerts.txt'):
                AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}AlertSummary.wav')
            getCurrentTime()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}CurrentTime.wav')
            
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}Forecast.wav')
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}MarineForecast.wav')
            getCurrentTime()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}CurrentTime.wav')
            
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}RegionalSummary.wav')
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}Observations.wav')
            getCurrentTime()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}CurrentTime.wav')
            
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}HWO.wav')
            if config.get('Forecast', {}).get('enableTropicalForecast'):
                AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}TWO.wav')
            
            getStationID()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}StationID.wav')
            getCurrentTime()
            AUDIO_SEQUENCE.append(f'bmh_wav{path_sep}CurrentTime.wav')
                

            
            # Check for RWT (Wednesdays 11 AM - 12 PM)
            now_dt = datetime.now()
            today_str = now_dt.strftime('%Y-%m-%d')
            is_rwt_window = now_dt.weekday() == 2 and 11 <= now_dt.hour < 12
            if is_rwt_window and last_rwt_date != today_str:
                log.info("[BMH] Injecting Required Weekly Test...")
                getRWT()
                if os.path.exists(f'bmh_wav{path_sep}RWT.wav'):
                    AUDIO_SEQUENCE.insert(0, f'bmh_wav{path_sep}RWT.wav')
                    last_rwt_date = today_str

            # Write the current AUDIO_SEQUENCE to playlist.txt for the sequencer (FFmpeg Concat format)
            log.info('[BMH] Updating live playlist: %s', ", ".join([os.path.basename(f) for f in AUDIO_SEQUENCE]))
            base_dir = os.path.dirname(os.path.abspath(__file__))
            playlist_path = os.path.join(base_dir, 'playlist.txt')
            with open(playlist_path, 'w') as pf:
                for audio_file in AUDIO_SEQUENCE:
                    # FFmpeg concat format requires 'file' prefix
                    # Ensure path is absolute for maximum stability in PM2
                    if not os.path.isabs(audio_file):
                        abs_audio_path = os.path.join(base_dir, audio_file)
                    else:
                        abs_audio_path = audio_file
                    
                    pf.write(f"file '{abs_audio_path}'\n")
            
            # Note: We no longer combine into a single file to keep the stream's time fresh.
            # The background noise mixing is now handled by the stream.sh transmitter.
            
            elapsed = time.time() - start_time
            # Sleep for 60 seconds to keep the time updated
            sleep_time = max(0, 60 - elapsed)
            
            log.info('[BMH] Cycle completed in %d seconds. Sleeping for %d seconds...', int(elapsed), int(sleep_time))
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        log.info('[BMH] Stopping BMH Emulation. Goodbye!')
        sys.exit(0)
    except Exception:
        log.error("[BMH] Error: %s", traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BMH Emulation')
    parser.add_argument('--config', default='config.json', help='Path to the config file')
    parser.add_argument('--generate-config', action='store_true', help='Generate a default config file and exit')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging output')
    parser.add_argument('--interactively-configure', action='store_true', help='Run interactive configuration setup')
    parser.add_argument('--rwt', action='store_true', help='Immediately trigger a Required Weekly Test (RWT)')
    args = parser.parse_args()

    try:
        if args.generate_config:
            log = setup_logging(args.verbose)
            from utils import generate_default_config
            generate_default_config(log)
            sys.exit(0)
        
        config = json.load(open(args.config, encoding='utf-8'))
        
        if args.interactively_configure:
            log = setup_logging(args.verbose, config.get("logLevel"))
            from utils import interactive_config_setup
            interactive_config_setup(log)
            sys.exit(0)
            
        log = setup_logging(args.verbose, config.get("logLevel"))
        if args.rwt:
            config['FORCE_RWT'] = True
        main(log, config)
        
    except FileNotFoundError:
        print(f"Error: {args.config} not found. Use --generate-config to create one.")
        sys.exit(1)
    except Exception as e:
        print(f"Critical Error: {e}")
        traceback.print_exc()
        sys.exit(1)
