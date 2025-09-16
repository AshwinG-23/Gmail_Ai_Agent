import os
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

def train_lora_extractor():
    # Clear GPU cache
    torch.cuda.empty_cache()
    
    # --- 1. Load Dataset ---
    dataset_path = "dataset.jsonl"
    print(f"Loading dataset from {dataset_path}...")
    
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found!")
        return
    
    dataset = load_dataset("json", data_files=dataset_path, split="train")
    dataset_split = dataset.train_test_split(test_size=0.1, seed=42)

    # --- 2. Load Base Model & Tokenizer ---
    model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
    print(f"Loading base model: {model_name}...")

    # More aggressive quantization for 8GB GPU
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        llm_int8_enable_fp32_cpu_offload=True,  # Offload some to CPU
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        trust_remote_code=True,
        device_map="auto",
        low_cpu_mem_usage=True,
    )
    
    model.config.use_cache = False
    if hasattr(model.config, 'pretraining_tp'):
        model.config.pretraining_tp = 1

    tokenizer = AutoTokenizer.from_pretrained(
        model_name, 
        trust_remote_code=True,
        padding_side="right"
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- 3. Configure LoRA ---
    print("Configuring LoRA...")
    lora_config = LoraConfig(
        r=8,  # Reduced from 16
        lora_alpha=16,  # Reduced from 32
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # --- 4. Configure SFTConfig for 8GB GPU ---
    print("Setting up SFTConfig...")
    training_args = SFTConfig(
        output_dir="./llama3-extractor-results",
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-5,
        logging_steps=10,
        bf16=True,
        save_strategy="epoch",
        eval_strategy="no",  # Disable evaluation to save memory
        save_total_limit=1,
        load_best_model_at_end=False,
        warmup_steps=10,
        dataset_text_field="text",
        max_length=1024,
        packing=False,
        gradient_checkpointing=True,
        dataloader_pin_memory=False,
        remove_unused_columns=True,
    )

    # --- 5. Initialize SFTTrainer ---
    print("Initializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset_split["train"],
        peft_config=lora_config,
        processing_class=tokenizer,
    )

    # --- 6. Start Training ---
    print("Starting LoRA fine-tuning...")
    try:
        trainer.train()
        print("Training completed successfully!")
    except Exception as e:
        print(f"Training failed with error: {e}")
        return

    # --- 7. Save the Final Adapter ---
    final_adapter_path = "./my-final-llama3-extractor"
    print(f"Saving LoRA adapter to {final_adapter_path}...")
    trainer.save_model(final_adapter_path)
    print(f"LoRA adapter saved to {final_adapter_path}")

if __name__ == "__main__":
    train_lora_extractor()
