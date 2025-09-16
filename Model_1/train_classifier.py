# train_classifier.py
import pandas as pd
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def train_model():
    # --- 1. Load Prepared Dataset from CSV ---
    print("Loading prepared dataset...")
    df = pd.read_csv('emails_prepared.csv')

    # Create mappings: string labels to integer IDs and vice versa
    unique_labels = sorted(df['label_text'].unique())
    label2id = {label: i for i, label in enumerate(unique_labels)}
    id2label = {i: label for i, label in enumerate(unique_labels)}
    
    # Add integer 'label' column
    df['label'] = df['label_text'].map(label2id)

    # Split data into training and testing sets
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label'])

    train_dataset = Dataset.from_pandas(train_df)
    test_dataset = Dataset.from_pandas(test_df)

    print("Dataset loaded and split.")

    # --- 2. Preprocess and Tokenize ---
    print("Tokenizing data...")
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=512)

    tokenized_train_dataset = train_dataset.map(tokenize_function, batched=True)
    tokenized_test_dataset = test_dataset.map(tokenize_function, batched=True)
    print("Tokenization complete.")

    # --- 3. Load the Model ---
    num_labels = len(unique_labels)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id
    )
    print(f"Loaded '{model_name}' model with {num_labels} labels.")

    # --- 4. Define Evaluation Metrics ---
    def compute_metrics(pred):
        labels = pred.label_ids
        preds = pred.predictions.argmax(-1)
        precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
        acc = accuracy_score(labels, preds)
        return {'accuracy': acc, 'f1': f1, 'precision': precision, 'recall': recall}

    # --- 5. Set Training Arguments ---
    training_args = TrainingArguments(
        output_dir="./email-classifier-results",
        num_train_epochs=3,
        per_device_train_batch_size=8, # Lower if you get CUDA out-of-memory errors
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=50,
        eval_strategy="epoch",  # FIXED: Changed from evaluation_strategy
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    # --- 6. Create and Run the Trainer ---
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_test_dataset,
        compute_metrics=compute_metrics,
    )

    print("Starting fine-tuning...")
    trainer.train()
    print("Fine-tuning complete.")

    # --- 7. Save the Final Model and Tokenizer ---
    final_model_path = "./my-final-email-classifier"
    trainer.save_model(final_model_path)
    tokenizer.save_pretrained(final_model_path)
    print(f"Best model and tokenizer saved to {final_model_path}")


if __name__ == '__main__':
    train_model()
