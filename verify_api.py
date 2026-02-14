 
import httpx
import json
import sys

def verify_api():
    url = "http://localhost:8000/api/analyze"
    print(f"Sending request to {url}...")
    
    try:
        files = {'file': open('test_fake.jpg', 'rb')}
        response = httpx.post(url, files=files, timeout=120.0)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ API Request Successful")
            print(f"Analysis ID: {data.get('analysis_id')}")
            
            # Check Risk Score
            risk = data.get('risk', {})
            score = risk.get('overall_score')
            level = risk.get('risk_level')
            print(f"Risk Score: {score}/100 ({level})")
            
            # Check Verdict
            verdict_data = data.get('verdict', {})
            print(f"Verdict: {verdict_data.get('verdict')}")
            
            # Check specific flags
            exif = data.get('exif', {})
            # Check flags list for Photoshop
            flags = exif.get('flags', [])
            found_photoshop = any("Photoshop" in flag for flag in flags)
            
            if found_photoshop:
                print("✅ Correctly detected Photoshop in EXIF")
            else:
                print(f"⚠️ Missed Photoshop detection in EXIF. Flags: {flags}")
                
            ai_gen = data.get('ai_detection', {})
            print(f"AI Generation Probability: {ai_gen.get('confidence')}%")

            if score > 40: # fake image should trigger at least medium risk
                print("\n✅ SUCCESS: High risk correctly identified.")
            else:
                print(f"\n⚠️ WARNING: Risk score {score} lower than expected for fake image.")

            # Check New Features
            print("\n------------------------------------------------")
            print("Checking InnoVision Feature Upgrades:")
            if "share_summary" in data:
                print(f"✅ Share Summary Generated: {data['share_summary']}")
            else:
                print("❌ Share Summary Missing")
            
            if "reverse_search_links" in data:
                print(f"✅ Reverse Search Links: {list(data['reverse_search_links'].keys())}")
            else:
                print("❌ Reverse Search Links Missing")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("Ensure server is running on localhost:8000")

if __name__ == "__main__":
    verify_api()
