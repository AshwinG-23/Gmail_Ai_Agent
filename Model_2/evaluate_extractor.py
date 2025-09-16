# evaluate_extractor.py

import torch
import json
from datasets import load_dataset
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from tqdm import tqdm

# --- Configuration ---
MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"
# Path to your newly trained LoRA adapter
ADAPTER_PATH = "./my-final-llama3-extractor"
DATASET_PATH = "dataset.jsonl"

def load_model_and_tokenizer():
    """Loads the base model and applies the fine-tuned LoRA adapter."""
    print("Loading base model and adapter for evaluation...")
    
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

    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    model.eval() # Set the model to evaluation mode
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    print("Model and tokenizer loaded successfully.")
    return model, tokenizer

def safe_json_parse(text):
    """Attempts to parse a JSON object from a string, returns None on failure."""
    try:
        # Find the first '{' and the last '}' to isolate the JSON object
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = text[json_start:json_end]
            return json.loads(json_str)
        return None
    except json.JSONDecodeError:
        return None

def run_evaluation():
    """Runs the full evaluation on the test set for the extractor model."""
    model, tokenizer = load_model_and_tokenizer()

    # 1. Load your test dataset
    dataset = load_dataset("json", data_files={"train": DATASET_PATH}, split="train")
    dataset_split = dataset.train_test_split(test_size=0.1, seed=42)
    test_dataset = dataset_split["test"]
    
    valid_json_count = 0
    exact_match_count = 0
    total_true_positives = 0
    total_false_positives = 0
    total_false_negatives = 0

    print(f"Running inference on {len(test_dataset)} test examples...")

    # 2. Loop through the test set and get predictions
    for item in tqdm(test_dataset):
        full_text = item['text']
        
        try:
            # Isolate the prompt to feed to the model
            prompt = full_text.split("<|start_header_id|>assistant<|end_header_id|>")[0] + "<|start_header_id|>assistant<|end_header_id|>"
            # Isolate the ground truth JSON for comparison
            gt_text = full_text.split("<|start_header_id|>assistant<|end_header_id|>")[1].replace("<|eot_id|>", "").strip()
            ground_truth_json = json.loads(gt_text)
        except (IndexError, json.JSONDecodeError):
            continue # Skip malformed rows in the dataset

        # Run inference
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=512, eos_token_id=tokenizer.eos_token_id, do_sample=False)
        
        input_length = inputs.input_ids.shape[1]
        prediction_text = tokenizer.decode(outputs[0, input_length:], skip_special_tokens=True)
        
        # 3. Calculate metrics for this prediction
        predicted_json = safe_json_parse(prediction_text)
        
        if predicted_json is not None:
            valid_json_count += 1
            
            # Check for exact match
            if predicted_json == ground_truth_json:
                exact_match_count += 1

            # Calculate field-level F1 score components
            gt_items = set(ground_truth_json.items())
            pred_items = set(predicted_json.items())
            
            true_positives = len(gt_items.intersection(pred_items))
            false_positives = len(pred_items - gt_items)
            false_negatives = len(gt_items - pred_items)
            
            total_true_positives += true_positives
            total_false_positives += false_positives
            total_false_negatives += false_negatives

    # 4. Calculate final metrics
    num_examples = len(test_dataset)
    validity_rate = valid_json_count / num_examples
    exact_match_rate = exact_match_count / num_examples
    
    # Calculate overall Precision, Recall, and F1
    precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 0
    recall = total_true_positives / (total_true_positives + total_false_negatives) if (total_true_positives + total_false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n--- Evaluation Results for Llama 3 Extractor ---")
    print(f"\nJSON Validity Rate: {validity_rate:.4f} ({valid_json_count}/{num_examples})")
    print(f"Exact Match Rate:   {exact_match_rate:.4f} ({exact_match_count}/{num_examples})")
    print("\n--- Field-Level Performance ---")
    print(f"Precision:          {precision:.4f}")
    print(f"Recall:             {recall:.4f}")
    print(f"F1-Score:           {f1_score:.4f}")


if __name__ == "__main__":
    run_evaluation()