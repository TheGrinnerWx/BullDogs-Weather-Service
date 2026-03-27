import os
import subprocess
import logging
import sys
import utils
from utils import produce_wav_file
from EAS import encode_eas_to_wav, generate_same_header

# Set up specialized logging for RWT
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RWT")

def getRWT():
    """
    Generates the Required Weekly Test (RWT) sequence.
    Sequence: SAME Header (x3) -> Attention Tone (1050Hz) -> Script -> EOM (x3)
    """
    logger.info("Starting RWT Generation Sequence...")
    
    config = utils.load_config()
    eas_config = config.get('EAS', {})
    eas_locations = eas_config.get('locations', ["036061"])
    eas_org = eas_config.get('originator', "WXR")
    eas_event = eas_config.get('eventCode', "RWT")
    purge_map = eas_config.get('purgeTimeMap', {})
    eas_purge = purge_map.get(eas_event, eas_config.get('purgeTime', "0015"))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    bmh_wav_dir = os.path.join(base_dir, "bmh_wav")
    os.makedirs(bmh_wav_dir, exist_ok=True)
    
    # Absolute paths for all components
    output_file = os.path.join(base_dir, "bmh_wav", "RWT.wav")
    script_wav = os.path.join(base_dir, "bmh_wav", "RWT_script.wav")
    attention_wav = os.path.join(base_dir, "bmh_wav", "attention_tone.wav")
    header_wav = os.path.join(base_dir, "bmh_wav", "same_header.wav")
    eom_wav = os.path.join(base_dir, "bmh_wav", "eom_tones.wav")
    silence_wav = os.path.join(base_dir, "bmh_wav", "silence.wav")
    
    sox_path = utils.SOX_PATH

    try:
        # 1. Generate silence (1 second) for spacing
        logger.info("Generating silence buffer...")
        subprocess.run([sox_path, "-n", "-r", "44100", "-c", "1", silence_wav, "trim", "0.0", "1.0"], check=True)

        # 2. Generate SAME Header (x1)
        header_text = generate_same_header(org=eas_org, eee=eas_event, locations=eas_locations, tttt=eas_purge)
        logger.info(f"Generating SAME Header: {header_text}")
        encode_eas_to_wav(header_text, header_wav)

        # 3. Generate EOM (x1)
        logger.info("Generating EOM Tones...")
        encode_eas_to_wav("NNNN", eom_wav)

        # 4. Generate 1050Hz Attention Tone (8 seconds)
        logger.info("Generating Attention Tone (8s)...")
        subprocess.run([sox_path, "-n", "-r", "44100", "-c", "1", attention_wav, "synth", "8.0", "sine", "1050"], check=True)

        # 5. Synthesize the Script
        script = (
            "This is a test of the bulldogs weather radio warning system. During potentially dangerous weather situations, "
            "specially built receivers can be automatically activated by these systems to warn of the impending hazard. "
            "Tests of these receivers and the alarm tone are normally conducted by the bulldogs weather service each Wednesday. "
            "If there is a threat of, or existing severe weather in the area on Wednesday, "
            "the test will be postponed until the next available good weather day. "
            "This concludes this test of the bulldogs weather radio warning system. We now return to regular programming."
        )
        logger.info("Synthesizing RWT script via Wine...")
        produce_wav_file(script, script_wav)

        # 6. Combine: [Header-Sil-Header-Sil-Header]-Sil-Attn-Script-Sil-[EOM-Sil-EOM-Sil-EOM]
        logger.info("Combining official RWT sequence (SoX)...")
        combine_cmd = [
            sox_path,
            header_wav, silence_wav, header_wav, silence_wav, header_wav, silence_wav,
            attention_wav,
            script_wav,
            silence_wav,
            eom_wav, silence_wav, eom_wav, silence_wav, eom_wav,
            output_file
        ]
        subprocess.run(combine_cmd, check=True)
        
        if os.path.exists(output_file):
            logger.info(f"SUCCESS: Created {output_file}")
            return True
        else:
            logger.error("FAILED: Output file was not created.")
            return False
            
    except Exception as e:
        logger.error(f"Error during RWT creation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    getRWT()
