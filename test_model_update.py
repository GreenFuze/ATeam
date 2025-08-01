#!/usr/bin/env python3

import requests
import json

def test_model_update():
    """Test the model update functionality for dual-capability models"""
    
    # Test data for llama3.1:8b_chat
    model_id = "llama3.1:8b_chat"
    model_config = {
        "name": "llama3.1:8b (Chat)",
        "description": "llama3.1:8b model from ollama (chat + embedding) - Chat capability",
        "context_window_size": 131072,
        "model_settings": {},
        "default_inference": {"stream": True, "think": True}
    }
    
    try:
        # Make the PUT request
        response = requests.put(
            f"http://localhost:8000/api/models/{model_id}",
            json=model_config,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Model update successful!")
        else:
            print("❌ Model update failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on port 8000.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_model_update() 