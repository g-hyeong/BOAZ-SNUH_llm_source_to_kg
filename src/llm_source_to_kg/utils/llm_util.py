from llm_source_to_kg.llm.gemini import GeminiLLM


def get_llm(llm_type: str, model: str = "gemini-2.0-flash"):
    if llm_type == "gemini":
        return GeminiLLM(model=model)
    else:
        raise ValueError(f"Invalid LLM type: {llm_type}")
    
