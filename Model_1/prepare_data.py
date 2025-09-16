# prepare_data.py
import json
import pandas as pd
import os

# --- Configuration ---
INPUT_JSON_PATH = 'gmail_labelled_gemini_shuffled.json'
OUTPUT_CSV_PATH = 'emails_prepared.csv'

def prepare_data():
    """
    Loads raw JSON data, combines relevant text fields,
    and saves it to a clean CSV file ready for training.
    """
    print(f"Loading data from {INPUT_JSON_PATH}...")
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"Error: Data file not found at '{INPUT_JSON_PATH}'")
        print("Please make sure your raw data JSON file is in the same directory.")
        return

    with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    processed_data = []
    for item in data:
        # Combine sender, subject, and body for a richer input text
        sender = item.get('sender', '')
        subject = item.get('subject', '')
        body = item.get('body', '')
        full_text = f"From: {sender}\nSubject: {subject}\n\n{body}"

        # Get the label
        label_text = item.get('classification')

        if label_text:  # Only include items that have a label
            processed_data.append({
                'text': full_text,
                'label_text': label_text
            })

    df = pd.DataFrame(processed_data)
    df.to_csv(OUTPUT_CSV_PATH, index=False)

    print(f"Successfully processed {len(df)} emails.")
    print(f"Clean data saved to {OUTPUT_CSV_PATH}")
    print(f"\nFound {len(df['label_text'].unique())} unique labels:")
    print(df['label_text'].value_counts())

if __name__ == '__main__':
    prepare_data()