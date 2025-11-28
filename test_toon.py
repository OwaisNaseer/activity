"""Test TOON encoding/decoding functionality."""
import sys
from utils.toon_utils import json_to_toon, toon_to_json

def test_toon_basic():
    """Test basic TOON encoding/decoding."""
    print("Testing TOON encoding/decoding...")
    
    # Test data
    test_data = {
        "subject": "Science",
        "grade_band": "5-6",
        "topic": "Robotics",
        "available_time": 45,
        "materials": "LEGO, sensors",
        "constraints": "Classroom space",
        "language": "English",
        "standard": "NGSS",
        "num_variants": 2
    }
    
    try:
        # Encode to TOON
        print("\n1. Encoding JSON to TOON...")
        toon_str = json_to_toon(test_data)
        print("TOON output:")
        print(toon_str)
        print("\n" + "="*50)
        
        # Decode back to JSON
        print("\n2. Decoding TOON back to JSON...")
        decoded_data = toon_to_json(toon_str)
        print("Decoded data:")
        print(decoded_data)
        print("\n" + "="*50)
        
        # Verify round-trip
        print("\n3. Verifying round-trip...")
        if decoded_data == test_data:
            print("✓ SUCCESS: Round-trip encoding/decoding works!")
            return True
        else:
            print("✗ FAILED: Data mismatch")
            print(f"Original: {test_data}")
            print(f"Decoded:  {decoded_data}")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_toon_basic()
    sys.exit(0 if success else 1)

