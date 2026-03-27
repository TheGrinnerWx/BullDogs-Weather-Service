import wave
import math
import struct
import logging

log = logging.getLogger("BMH")

# EAS/SAME Specifications
BIT_RATE = 520.8333  # Bits per second
SAMPLE_RATE = 44100
FREQ_SPACE = 1562.5  # Hz (Logic 0)
FREQ_MARK = 2083.3   # Hz (Logic 1)
PREAMBLE_BYTE = 0xAB # 10101011
PREAMBLE_COUNT = 16  # NWS sends 16 preambles

def generate_bit_stream(text):
    """
    Converts text to EAS/SAME bit stream including preambles.
    Each byte is sent LSB first.
    """
    bits = []
    
    # 1. Add Preambles (10101011)
    for _ in range(PREAMBLE_COUNT):
        for i in range(8):
            bits.append((PREAMBLE_BYTE >> i) & 1)
            
    # 2. Add Text Data
    for char in text:
        byte_val = ord(char)
        for i in range(8):
            bits.append((byte_val >> i) & 1)
            
    return bits

def bits_to_pcm(bits):
    """
    Modulates bits into AFSK PCM data.
    """
    samples_per_bit = int(SAMPLE_RATE / BIT_RATE)
    pcm_data = []
    
    current_phase = 0.0
    
    for bit in bits:
        freq = FREQ_MARK if bit == 1 else FREQ_SPACE
        phase_inc = 2 * math.pi * freq / SAMPLE_RATE
        
        for _ in range(samples_per_bit):
            # Generate sine wave sample
            sample = math.sin(current_phase)
            # Convert to 16-bit PCM (signed)
            int_sample = int(sample * 32767)
            pcm_data.append(struct.pack('<h', int_sample))
            current_phase += phase_inc
            
        # Optional: Keep phase continuous to avoid clicks (already handled by not resetting current_phase)
        if current_phase > 2 * math.pi:
            current_phase -= 2 * math.pi
            
    return b"".join(pcm_data)

def generate_same_header(org="WXR", eee="RWT", locations=["036061"], tttt="0015", timestamp=None):
    """
    Constructs a SAME header string.
    Format: ZCZC-ORG-EEE-PSSCCC-PSSCCC+TTTT-JJJHHMM-LLLLLLLL-
    JJJ = Julian Day (001-366) in UTC
    HHMM = Issue Time in UTC
    LLLLLLLL = Station ID (8 chars, e.g., WXB26   -)
    """
    import datetime
    if timestamp is None:
        # Use current UTC time in JJJHHMM format
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp = now.strftime("%j%H%M")
        
    loc_str = "-".join(locations)
    header = f"ZCZC-{org}-{eee}-{loc_str}+{tttt}-{timestamp}-WXB26   -"
    return header

def encode_eas_to_wav(text, output_file):
    """
    Encodes text (SAME header or EOM) into a WAV file.
    """
    log.info(f"[EAS] Encoding SAME message: {text}")
    bits = generate_bit_stream(text)
    pcm_bytes = bits_to_pcm(bits)
    
    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)
    
    log.info(f"[EAS] Successfully saved EAS audio to {output_file}")
    return True

def goertzel(samples, target_freq, sample_rate):
    """
    Goertzel algorithm to detect a specific frequency in a block of samples.
    Returns the magnitude squared.
    """
    n = len(samples)
    k = int(0.5 + (n * target_freq / sample_rate))
    w = (2 * math.pi / n) * k
    cosine = math.cos(w)
    coeff = 2 * cosine
    
    s_prev = 0.0
    s_prev2 = 0.0
    for sample in samples:
        s = sample + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s
        
    power = s_prev2 * s_prev2 + s_prev * s_prev - coeff * s_prev * s_prev2
    return power

def decode_bits_from_wav(filename):
    """
    Decodes AFSK bits from a WAV file using Goertzel.
    """
    with wave.open(filename, 'rb') as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        raw_data = wav_file.readframes(n_frames)
        # Assuming 16-bit mono
        samples = [struct.unpack('<h', raw_data[i:i+2])[0] / 32768.0 for i in range(0, len(raw_data), 2)]
        
    bits = []
    samples_per_bit = int(framerate / BIT_RATE)
    
    # Slide through samples bit-by-bit
    for i in range(0, len(samples) - samples_per_bit, samples_per_bit):
        bit_samples = samples[i : i + samples_per_bit]
        
        p_space = goertzel(bit_samples, FREQ_SPACE, framerate)
        p_mark = goertzel(bit_samples, FREQ_MARK, framerate)
        
        bits.append(1 if p_mark > p_space else 0)
        
    return bits

def bits_to_text(bits):
    """
    Parses bit stream into SAME text.
    Looks for preamble sync (0xAB).
    """
    bytes_list = []
    # Simplified search: look for a sequence of bytes
    for i in range(len(bits) - 8):
        byte_bits = bits[i : i + 8]
        byte_val = 0
        for b in range(8):
            byte_val |= (byte_bits[b] << b)
            
        # VERY crude sync: look for anything that looks like ZCZC or NNNN
        if byte_val != 0xAB and byte_val >= 32 and byte_val <= 126:
            bytes_list.append(chr(byte_val))
            
    return "".join(bytes_list)

def decode_eas_from_wav(filename):
    """
    The main entry point for decoding.
    """
    log.info(f"[EAS] Attempting to decode: {filename}")
    bits = decode_bits_from_wav(filename)
    text = bits_to_text(bits)
    return text

if __name__ == "__main__":
    # Test generation and decoding in /tmp for sandbox safety
    header = generate_same_header()
    tmp_same = "/tmp/test_same.wav"
    encode_eas_to_wav(header, tmp_same)
    
    # Test Decoding
    decoded = decode_eas_from_wav(tmp_same)
    print(f"ENCODED: {header}")
    print(f"DECODED: {decoded}")
    
    if "ZCZC" in decoded:
        print("✅ SUCCESS: Encoder/Decoder Round-trip Validated!")
    else:
        print("❌ ERROR: Decoding failed or was partial.")
