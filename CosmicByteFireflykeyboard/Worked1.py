import hid
import time

VID = 0x04D9
PID = 0xA1CD

# ─── HARDWARE EFFECTS REGISTRY ───────────────────────────────────────
class Effects:
    STATIC = 0
    BREATHE = 1
    FADE = 2
    GETTING_OFF = 3
    LITTLE_STARS = 4
    LASER = 5
    WAVE = 6
    NEON = 7
    RAINDROP = 8
    RIPPLE = 9
    WAVE2 = 10
    SWIRL = 11

class FireflyController:
    def __init__(self):
        self.device = hid.device()
        self.target_path = None
        self._find_interface()

    def _find_interface(self):
        print("🔍 Searching for Keyboard Interface 2 (MI_02)...")
        for dev in hid.enumerate(VID, PID):
            path = dev.get('path', b'').decode(errors='ignore') if isinstance(dev.get('path'), bytes) else str(dev.get('path', ''))
            
            # The Rust script targets Interface 2. On Windows, this is labeled as mi_02.
            if "mi_02" in path.lower() or dev.get('usage_page', 0) >= 0xFF00:
                self.target_path = dev.get('path')
                print(f"✓ Found exact hardware interface!")
                break
                
        if not self.target_path:
            raise Exception("Could not find Interface 2. Make sure official software is closed!")

    def connect(self):
        self.device.open_path(self.target_path)
        self.device.set_nonblocking(True)
        print("✓ Connected successfully.")

    def disconnect(self):
        self.device.close()
        print("Disconnected.")

    # ─── THE 3 HARDWARE COMMANDS (Translated from Rust) ──────────────

    def send_header(self):
        """Rust: execute_header_request()"""
        print("→ Sending Handshake...")
        # hidapi send_feature_report requires a 0x00 at the front for Report ID 0
        data = b'\x00\x30\x00\x00\x00\x00\x55\xaa\x00'
        self.device.send_feature_report(data)
        time.sleep(0.02)

    def send_colors(self, hex_colors):
        """Rust: execute_color_request()"""
        if len(hex_colors) != 7:
            raise ValueError("Exactly 7 colors are required by the hardware.")
            
        print("→ Sending Color Palette...")
        color_bytes = []
        for hex_code in hex_colors:
            # Strip the '#' and convert to 6-bit RGB (Divide by 4 / bitshift >> 2)
            hex_code = hex_code.lstrip('#')
            r = int(hex_code[0:2], 16) >> 2
            g = int(hex_code[2:4], 16) >> 2
            b = int(hex_code[4:6], 16) >> 2
            color_bytes.extend([r, g, b])
            
        # Pad with zeros to reach exactly 64 bytes of data
        padding = [0] * (64 - len(color_bytes))
        
        # Prepend 0x00 for the interrupt write
        payload = b'\x00' + bytes(color_bytes + padding)
        self.device.write(payload)
        time.sleep(0.02)

    def send_effect(self, effect_id, color_index=7):
        """Rust: execute_effects_request()"""
        print(f"→ Triggering Effect ID: {effect_id}...")
        # color_index 0-6 locks the effect to one specific color from your palette. 
        # color_index 7 tells the hardware to cycle through all 7 colors.
        data = bytes([0x00, 0x08, effect_id, 0x3f, 0x01, 0x00, color_index, 0xc4, 0x3b])
        self.device.send_feature_report(data)
        time.sleep(0.02)


# ─── HOW TO USE IT ───────────────────────────────────────────────────
if __name__ == "__main__":
    
    # 1. Define your 7 colors (Must be exactly 7!)
    my_colors = [
        "#FF0000", # Red
        "#FF7F00", # Orange
        "#FFFF00", # Yellow
        "#00FF00", # Green
        "#0000FF", # Blue
        "#4B0082", # Indigo
        "#8B00FF"  # Violet
    ]
    
    # 2. Pick your effect from the Effects class
    # Try Effects.WAVE, Effects.LASER, Effects.RAINDROP, etc.
    my_effect = Effects.STATIC
    
    try:
        kb = FireflyController()
        kb.connect()
        
        kb.send_header()
        kb.send_colors(my_colors)
        
        # We pass 7 as the color_index so it uses ALL the colors in the wave.
        kb.send_effect(my_effect, color_index=7)
        
        print("\n🎉 Success! The hardware should now be running the effect.")
        kb.disconnect()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")