"""
BMP Steganography - Functional Programming Approach
Completely different structure using functions instead of classes
"""

import os
import sys

# Global constants
DELIMITER = "###END###"
BITS_PER_BYTE = 8

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def string_to_binary(text):
    """Convert string to binary string"""
    binary_str = ''.join(format(ord(char), '08b') for char in text)
    return binary_str


def binary_to_string(binary_str):
    """Convert binary string to text"""
    chars = []
    for i in range(0, len(binary_str), BITS_PER_BYTE):
        byte = binary_str[i:i+BITS_PER_BYTE]
        if len(byte) == BITS_PER_BYTE:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)


def read_int(file, bytes_count, signed=False):
    """Read integer from file"""
    return int.from_bytes(file.read(bytes_count), byteorder='little', signed=signed)


def write_int(file, value, bytes_count, signed=False):
    """Write integer to file"""
    file.write(value.to_bytes(bytes_count, byteorder='little', signed=signed))


# ============================================================================
# BMP FILE OPERATIONS
# ============================================================================

def load_bmp_file(filepath):
    """
    Load BMP file and return header info and pixel data
    Returns: (width, height, pixels, header_bytes)
    """
    print(f"📂 Loading {filepath}...")
    
    with open(filepath, 'rb') as f:
        # Read signature
        signature = f.read(2)
        if signature != b'BM':
            raise ValueError("Not a valid BMP file")
        
        # Read file size and data offset
        file_size = read_int(f, 4)
        f.read(4)  # Skip reserved bytes
        data_offset = read_int(f, 4)
        
        # Read DIB header
        header_size = read_int(f, 4)
        width = read_int(f, 4, signed=True)
        height = read_int(f, 4, signed=True)
        planes = read_int(f, 2)
        bits_per_pixel = read_int(f, 2)
        
        if bits_per_pixel != 24:
            raise ValueError(f"Only 24-bit BMP supported (got {bits_per_pixel}-bit)")
        
        # Skip rest of header
        f.read(24)
        
        # Save header for later
        f.seek(0)
        header_bytes = f.read(data_offset)
        
        # Read pixel data
        f.seek(data_offset)
        width = abs(width)
        height = abs(height)
        
        padding = (4 - (width * 3) % 4) % 4
        
        pixels = []
        for row in range(height):
            row_pixels = []
            for col in range(width):
                b = read_int(f, 1)
                g = read_int(f, 1)
                r = read_int(f, 1)
                row_pixels.append([b, g, r])
            f.read(padding)  # Skip padding
            pixels.append(row_pixels)
    
    print(f"✅ Loaded {width}x{height} BMP")
    return width, height, pixels, header_bytes, padding


def save_bmp_file(filepath, width, height, pixels, header_bytes, padding):
    """Save pixel data back to BMP file"""
    print(f"💾 Saving {filepath}...")
    
    with open(filepath, 'wb') as f:
        # Write header
        f.write(header_bytes)
        
        # Write pixel data
        for row in pixels:
            for pixel in row:
                f.write(bytes(pixel))
            f.write(b'\x00' * padding)
    
    print(f"✅ Saved successfully!")


# ============================================================================
# ENCODING FUNCTIONS
# ============================================================================

def calculate_capacity(width, height):
    """Calculate maximum message capacity in characters"""
    total_bits = width * height * 3  # 3 color channels per pixel
    total_chars = total_bits // BITS_PER_BYTE
    return total_chars


def encode_message_in_pixels(pixels, width, height, message):
    """
    Encode message into pixel LSBs
    Returns: modified pixels
    """
    # Add delimiter
    full_message = message + DELIMITER
    
    # Convert to binary
    binary_message = string_to_binary(full_message)
    
    print(f"🔄 Encoding {len(full_message)} characters ({len(binary_message)} bits)...")
    
    bit_index = 0
    total_bits = len(binary_message)
    
    # Encode bits into pixels
    for row_idx in range(height):
        if bit_index >= total_bits:
            break
            
        for col_idx in range(width):
            if bit_index >= total_bits:
                break
            
            # Get pixel (it's a reference, so changes persist)
            pixel = pixels[row_idx][col_idx]
            
            # Encode in B, G, R channels
            for channel in range(3):
                if bit_index >= total_bits:
                    break
                
                # Get current bit
                bit = int(binary_message[bit_index])
                
                # Modify LSB: clear it first, then set to message bit
                pixel[channel] = (pixel[channel] & 0xFE) | bit
                
                bit_index += 1
            
            # Progress indicator
            if bit_index % 1000 == 0:
                progress = (bit_index / total_bits) * 100
                print(f"   Progress: {progress:.1f}%", end='\r')
    
    print(f"\n✅ Encoded {bit_index} bits!")
    return pixels


# ============================================================================
# DECODING FUNCTIONS
# ============================================================================

def decode_message_from_pixels(pixels, width, height):
    """
    Extract message from pixel LSBs
    Returns: decoded message
    """
    print(f"🔄 Extracting message...")
    
    binary_data = []
    max_bits = width * height * 3
    
    # Extract LSBs
    for row_idx in range(height):
        for col_idx in range(width):
            pixel = pixels[row_idx][col_idx]
            
            for channel in range(3):
                # Extract LSB
                bit = pixel[channel] & 1
                binary_data.append(str(bit))
                
                # Stop if we have enough bits (limit search)
                if len(binary_data) >= min(max_bits, 100000):
                    # Try to find delimiter periodically
                    if len(binary_data) % 8000 == 0:
                        temp_text = binary_to_string(''.join(binary_data))
                        if DELIMITER in temp_text:
                            # Found it! Stop reading
                            text_result = temp_text.split(DELIMITER)[0]
                            print(f"✅ Found message! ({len(text_result)} characters)")
                            return text_result
    
    # Convert all collected bits
    binary_string = ''.join(binary_data)
    full_text = binary_to_string(binary_string)
    
    # Look for delimiter
    if DELIMITER in full_text:
        message = full_text.split(DELIMITER)[0]
        print(f"✅ Extracted message! ({len(message)} characters)")
        return message
    else:
        print("⚠️  Warning: Delimiter not found")
        # Return printable characters only
        printable = ''.join(c for c in full_text[:500] if c.isprintable())
        return printable[:200]


# ============================================================================
# USER INTERFACE FUNCTIONS
# ============================================================================

def get_file_path(prompt, must_exist=True):
    """Get file path from user with validation"""
    while True:
        filepath = input(prompt).strip()
        
        if not filepath:
            print("❌ Path cannot be empty")
            continue
        
        if must_exist and not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            
            # Try to help find it
            filename = os.path.basename(filepath)
            current_files = [f for f in os.listdir('.') if f.endswith('.bmp')]
            
            if current_files:
                print(f"   📋 BMP files in current directory:")
                for f in current_files:
                    print(f"      - {f}")
            continue
        
        return filepath


def encode_workflow():
    """Handle encoding workflow"""
    print("\n" + "="*60)
    print("🔒 ENCODE MODE - Hide Your Message")
    print("="*60)
    
    try:
        # Get input file
        input_path = get_file_path("\n📁 Input BMP file: ", must_exist=True)
        
        # Load BMP
        width, height, pixels, header_bytes, padding = load_bmp_file(input_path)
        
        # Show capacity
        capacity = calculate_capacity(width, height)
        print(f"📊 Image can hold up to {capacity} characters")
        
        # Get message
        print(f"\n📝 Enter your secret message:")
        message = input("Message: ").strip()
        
        if not message:
            print("❌ Message cannot be empty")
            return
        
        # Check capacity
        if len(message) + len(DELIMITER) > capacity:
            print(f"❌ Message too long! Maximum: {capacity - len(DELIMITER)} characters")
            return
        
        # Encode
        modified_pixels = encode_message_in_pixels(pixels, width, height, message)
        
        # Get output file
        output_path = get_file_path("\n💾 Output BMP file: ", must_exist=False)
        
        # Save
        save_bmp_file(output_path, width, height, modified_pixels, header_bytes, padding)
        
        print(f"\n🎉 Success! Message hidden in {output_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def decode_workflow():
    """Handle decoding workflow"""
    print("\n" + "="*60)
    print("🔓 DECODE MODE - Extract Hidden Message")
    print("="*60)
    
    try:
        # Get input file
        input_path = get_file_path("\n📁 Encoded BMP file: ", must_exist=True)
        
        # Load BMP
        width, height, pixels, _, _ = load_bmp_file(input_path)
        
        # Decode
        message = decode_message_from_pixels(pixels, width, height)
        
        # Display result
        print("\n" + "="*60)
        print("📨 EXTRACTED MESSAGE:")
        print("="*60)
        print(message)
        print("="*60)
        
        # Option to save
        save_choice = input("\n💾 Save message to text file? (y/n): ").strip().lower()
        if save_choice == 'y':
            output_file = input("Output filename: ").strip()
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(message)
                print(f"✅ Saved to {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def show_menu():
    """Display main menu and get user choice"""
    print("\n" + "="*60)
    print("📋 MENU:")
    print("="*60)
    print("  1. Hide a message (Encode)")
    print("  2. Extract a message (Decode)")
    print("  3. Exit")
    print("="*60)
    
    choice = input("\nEnter your choice (1-3): ").strip()
    return choice


def main():
    """Main application entry point"""
    # Change to Downloads folder
    downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
    if os.path.exists(downloads):
        os.chdir(downloads)
        print(f"📂 Working directory: {downloads}\n")
    
    print("="*60)
    print("🔐 BMP STEGANOGRAPHY TOOL")
    print("   Functional Programming Version")
    print("="*60)
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            encode_workflow()
        elif choice == '2':
            decode_workflow()
        elif choice == '3':
            print("\n👋 Thank you for using BMP Steganography Tool!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3")
    
    input("\nPress Enter to exit...")


# ============================================================================
# PROGRAM ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)