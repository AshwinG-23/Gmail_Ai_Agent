# evaluate_distilbert_classifier.py (Final Version)

import torch
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from tqdm import tqdm

# --- Configuration ---
MODEL_PATH = "my-final-email-classifier"
# --- 1. Use the dataset that has both email body and category columns ---
# You might need to confirm this is the correct filename from your data pipeline
DATASET_PATH = "emails_prepared.csv"  # Ensure this CSV has 'body' and 'Category' columns

def load_model_and_tokenizer():
    """Loads a fine-tuned DistilBERT model and tokenizer from a local path."""
    print(f"Loading model and tokenizer from {MODEL_PATH}...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model.eval()
    print("Model and tokenizer loaded successfully.")
    return model, tokenizer, device

def run_evaluation():
    """Runs the full evaluation on the test set."""
    model, tokenizer, device = load_model_and_tokenizer()

    # --- 2. Load the CSV directly ---
    dataset = load_dataset("csv", data_files=DATASET_PATH, split="train")
    dataset_split = dataset.train_test_split(test_size=0.2, seed=42)
    test_dataset = dataset_split["test"]
    
    y_true = []
    y_pred = []

    id2label = model.config.id2label
    
    print(f"Running inference on {len(test_dataset)} test examples...")

    # --- 3. Loop directly over the correct columns ('body' and 'Category') ---
    for item in tqdm(test_dataset):
        email_text = item['text']
        ground_truth_label = item['label_text']
        
        # Ensure the data is valid before processing
        if not isinstance(email_text, str) or not isinstance(ground_truth_label, str):
            continue

        # Tokenize the input email text
        inputs = tokenizer(email_text, return_tensors="pt", truncation=True, padding=True, max_length=512).to(device)
        
        # Get model prediction
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits

        # Find the class with the highest probability
        predicted_class_id = torch.argmax(logits, dim=1).item()
        predicted_label = id2label[predicted_class_id]
        
        y_true.append(ground_truth_label)
        y_pred.append(predicted_label)
        
    # 4. Calculate and print the metrics
    print("\n--- Evaluation Results for DistilBERT Classifier ---")
    
    labels = sorted(list(set(y_true)))

    accuracy = accuracy_score(y_true, y_pred)
    print(f"\nOverall Accuracy: {accuracy:.4f}\n")

    print("Classification Report:")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))

    print("Confusion Matrix:")
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    print(cm_df)
    
    plt.figure(figsize=(10, 7))
    sns.heatmap(cm_df, annot=True, fmt='g', cmap='Blues')
    plt.title('DistilBERT Classifier - Confusion Matrix')
    plt.ylabel('Actual Labels')
    plt.xlabel('Predicted Labels')
    plt.tight_layout()
    plt.savefig('distilbert_confusion_matrix.png')
    print("\nConfusion matrix saved to distilbert_confusion_matrix.png")

if __name__ == "__main__":
    run_evaluation()