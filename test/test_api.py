import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import openai

load_dotenv()

def test_api_connection():
    api_key = os.getenv("AI_API_KEY")
    model = os.getenv("AI_MODEL")
    base_url = os.getenv("AI_BASE_URL")
    
    print("="*60)
    print("API Configuration Test")
    print("="*60)
    print(f"API Key: {api_key[:20]}..." if api_key else "API Key: NOT SET")
    print(f"Model: {model}")
    print(f"Base URL: {base_url}")
    print("="*60)
    
    if not api_key:
        print("ERROR: API Key not found in environment variables!")
        return False
    
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print("\nSending test request to API...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个视频分类助手。"},
                {"role": "user", "content": "请回复'API连接成功'"}
            ],
            temperature=0.3,
            max_tokens=50
        )
        
        print("\n" + "="*60)
        print("SUCCESS! API Connection Working!")
        print("="*60)
        print(f"Response: {response.choices[0].message.content}")
        print(f"Model used: {response.model}")
        print(f"Tokens used: {response.usage.total_tokens}")
        print("="*60)
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("ERROR! API Connection Failed!")
        print("="*60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("="*60)
        return False

if __name__ == "__main__":
    test_api_connection()
