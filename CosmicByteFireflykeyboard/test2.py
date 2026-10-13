import hid
import time
import sys

VID = 0x04D9
PID = 0xA1CD

class FireflyPerKeyController:
    def __init__(self):
        self.device = hid.device()
        self.target_path = None
        self._find_interface()

    def _find_interface(self):
        print("🔍 Searching for Keyboard Interface 2 (MI_02)...")
        for dev in hid.enumerate(VID, PID):
            path = dev.get('path', b'').decode(errors='ignore') if isinstance(dev.get('path'), bytes) else str(dev.get('path', ''))
            
            if "mi_02" in path.lower() or dev.get('usage_page', 0) >= 0xFF00:
                self.target_path = dev.get('path')
                print(f"✓ Found exact hardware interface!")
                break
                
        if not self.target_path:
            raise Exception("Could not find Interface 2. Make sure official software is closed!")

    def connect(self):
        self.device.open_path(self.target_path)
        # CRITICAL FIX: We do NOT use set_nonblocking(True) here. 
        # We need blocking mode to ensure all 13 packets arrive without dropping.
        print("✓ Connected successfully in BLOCKING mode.")

    def disconnect(self):
        self.device.close()
        print("Disconnected.")

    def send_header(self):
        print("→ Sending Handshake...")
        data = b'\x00\x30\x00\x00\x00\x00\x55\xaa\x00'
        self.device.send_feature_report(data)
        time.sleep(0.05)

    def send_per_key_colors(self, layout):
        print("→ Formatting 819-byte Per-Key Matrix...")
        
        # Create a blank canvas of 819 bytes (13 chunks * 63 bytes)
        stream = [0] * 819
        
        # Inject the colors from your dictionary into the hardware stream
        for key_index, hex_code in layout.items():
            base_pos = key_index * 3
            if base_pos + 2 < len(stream):
                hex_code = hex_code.lstrip('#')
                # Convert standard HEX to the hardware's 6-bit format
                stream[base_pos] = int(hex_code[0:2], 16) >> 2
                stream[base_pos + 1] = int(hex_code[2:4], 16) >> 2
                stream[base_pos + 2] = int(hex_code[4:6], 16) >> 2

        print("→ Firing 13 Indexed Packets...")
        # Slice the data into exactly 13 chunks of 63 bytes
        for packet_index in range(13):
            chunk = stream[packet_index * 63 : (packet_index + 1) * 63]
            
            # [0x00 Report ID] + [Packet Index 00, 01, 02...] + [63 Bytes of Color Data]
            payload = b'\x00' + bytes([packet_index]) + bytes(chunk)
            
            self.device.write(payload)
            time.sleep(0.01) # Let the hardware breathe

    def save_custom_layout(self):
        print("→ Burning to Flash Memory (Custom 0x33 Profile)...")
        # The exact custom layout trigger intercepted from the Ghidra C++ dump
        data = bytes([0x00, 0x08, 0x33, 0x3f, 0x04, 0x00, 0x00, 0xc4, 0x3b])
        self.device.send_feature_report(data)
        time.sleep(0.5)


if __name__ == "__main__":
    # Create your custom layout using standard Hex Codes!
    # The dictionary key is the hardware switch index (0 to 105).
    my_layout = {}
    
    # 1. Fill the entire board with a dim Steel Cyan background
    for i in range(106):
        my_layout[i] = "#0a1414" 
        
    # 2. Paint your core keys Blood Crimson
    my_layout[0] = "#FF0000"  # ESC
    my_layout[22] = "#FF0000" # W (Standard Holtek Index)
    my_layout[31] = "#FF0000" # A (Standard Holtek Index)
    my_layout[32] = "#FF0000" # S (Standard Holtek Index)
    my_layout[33] = "#FF0000" # D (Standard Holtek Index)

    try:
        kb = FireflyPerKeyController()
        kb.connect()
        
        kb.send_header()
        kb.send_per_key_colors(my_layout)
        kb.save_custom_layout()
        
        print("\n🎉 Success! Your custom per-key matrix is permanently applied.")
        kb.disconnect()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")