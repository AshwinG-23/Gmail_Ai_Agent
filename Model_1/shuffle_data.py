import pandas as pd
import json

# --- Configuration ---
# The path to your original, unshuffled JSON data file
INPUT_JSON_PATH = 'gmail_all_emails_5678_classified_single.json'

# The path where the new, shuffled JSON file will be saved
OUTPUT_JSON_PATH = 'gmail_labelled_gemini_shuffled.json'

def shuffle_dataset():
    """
    Loads a dataset from a JSON file, shuffles it completely,
    and saves it to a new JSON file.
    """
    print(f"Loading dataset from '{INPUT_JSON_PATH}'...")
    
    # Load the entire JSON file into a pandas DataFrame
    # A DataFrame is like a smart spreadsheet, perfect for this task
    df = pd.read_json(INPUT_JSON_PATH)
    
    print(f"Original dataset has {len(df)} entries.")
    
    # --- The Magic Step: Shuffling ---
    # .sample(frac=1) shuffles the DataFrame by taking a 100% random sample of rows.
    # .reset_index(drop=True) cleans up the old index numbers.
    df_shuffled = df.sample(frac=1).reset_index(drop=True)
    
    print("Dataset has been shuffled successfully.")
    
    # Save the shuffled DataFrame back to a JSON file
    # orient='records' and indent=2 will make it look nice and structured like the original
    df_shuffled.to_json(OUTPUT_JSON_PATH, orient='records', indent=2)
    
    print(f"Shuffled dataset saved to '{OUTPUT_JSON_PATH}'.")

if __name__ == '__main__':
    shuffle_dataset()