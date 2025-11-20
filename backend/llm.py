import requests
import json
import yaml

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def chat_completion(messages, model=None):
    config = load_config()
    llm_config = config.get("llm", {})
    
    api_key = llm_config.get("api_key")
    base_url = llm_config.get("base_url", "https://openrouter.ai/api/v1")
    default_model = llm_config.get("model", "openai/gpt-4o")
    
    if not api_key:
        raise ValueError("OpenRouter API Key not found in config.yaml")

    url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8501", # Localhost for streamlit
        "X-Title": "Hearing App",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model or default_model,
        "messages": messages
    }
    
    response = None
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"LLM Request failed: {e}")
        if response:
            print(f"Response: {response.text}")
        return None

def split_text_by_meaning(text, max_length=80):
    """
    Uses LLM to split text into meaningful segments.
    """
    prompt = f"""
    Split the following text into smaller, meaningful segments for subtitle generation.
    Each segment should be roughly under {max_length} characters if possible, but prioritize meaning.
    Return the result as a JSON list of strings.
    
    Text: "{text}"
    """
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that splits text into subtitles."},
        {"role": "user", "content": prompt}
    ]
    
    response = chat_completion(messages)
    if response:
        content = response['choices'][0]['message']['content']
        # Try to parse JSON from the response
        try:
            # Clean up code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except json.JSONDecodeError:
            print("Failed to parse LLM response as JSON. Returning original text.")
            return [text]
    return [text]
