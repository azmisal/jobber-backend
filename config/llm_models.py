# Supported LLM models for Jobber/Nexus CV
# Fill in the model names and display names as needed

SUPPORTED_LLM_MODELS=[
  {"id": "groq", "name": "Groq (Llama 3)", "env": "JOBBER_GROQ_API_KEY"},
  {"id": "ollama", "name": "Ollama (Llama 2, Mistral, etc.)", "env": "OLLAMA_BASE_URL"},
  {"id": "huggingface", "name": "Hugging Face (Free Tier)", "env": "HUGGINGFACE_API_KEY"},
  {"id": "openrouter", "name": "OpenRouter (Free Tier)", "env": "OPENROUTER_API_KEY"},
  {"id": "replicate", "name": "Replicate (Free Tier)", "env": "REPLICATE_API_KEY"}
]
