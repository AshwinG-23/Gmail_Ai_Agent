import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

# --- Configuration ---
MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"
ADAPTER_PATH = "./my-final-llama3-extractor"

def load_model_and_tokenizer():
    """
    Loads the 4-bit quantized base model and applies the LoRA adapter.
    Also configures the tokenizer correctly for generation.
    """
    print("Loading base model and adapter...")
    
    # --- SIMPLIFIED: Use the same bnb_config from your training script ---
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Load the LoRA adapter onto the base model
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    
    # --- SIMPLIFIED: The standard way to set the pad token for decoder-only models ---
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left" # Correct for batched generation

    print("Model and tokenizer loaded successfully.")
    return model, tokenizer

def extract_json(prompt_text, model, tokenizer, max_new_tokens=256):
    """
    Generates a response from the model given a prompt.
    """
    inputs = tokenizer(
        prompt_text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1024,
    ).to(model.device)

    # Get the length of the input prompt in tokens
    # CORRECTED: Use .shape[1] to get the sequence length
    input_length = inputs.input_ids.shape[1]

    # Generate tokens
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            eos_token_id=tokenizer.eos_token_id,
            do_sample=False, # Use greedy decoding for consistent results
        )

    # Decode the newly generated tokens
    # CORRECTED: Slice the output tensor correctly to get only the new tokens
    generated_tokens = outputs[0, input_length:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    
    return generated_text

if __name__ == "__main__":
    model, tokenizer = load_model_and_tokenizer()

    # --- SIMPLIFIED: A cleaner prompt that matches your training format ---
    email_text = "DevWorks is looking for a Backend Developer in Bangalore. Apply here: devworks.io/apply"
    
    prompt = f"""<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Extract structured data from this email. Email: '{email_text}'<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

    print("\n--- Running Inference ---")
    try:
        result = extract_json(prompt, model, tokenizer)
        print("\nPrediction:\n", result)
    except Exception as e:
        print(f"\nAn error occurred: {e}")