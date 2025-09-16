# inference.py
from transformers import pipeline

# Load the fine-tuned model from the local directory
model_path = "./my-final-email-classifier"
classifier = pipeline("text-classification", model=model_path)

print("Model loaded. Ready for inference.")

# --- Test Emails ---
email_1 = """
From: noreply@unstop.news
Subject: Codeforces Round 1047 (Div. 3)

The Tata Group is hiring at INR 27 LPA* & you are eligible

​​​​​​​Rewards:

Internship Opportunity with Tata Group
Grand Cash prize* of Rs. 2.5 lakhs
Luxury holiday experience at the Taj Hotels worth INR 50,000*
Many other prizes*
Eligibility: Full time students above 18 years of age
"""

email_2 = """
From: Dr. Anya Sharma <anya.s@iitgoa.ac.in>
Subject: IIT Goa's Anime community - Rakuen. Recruitment now open!!!

Greetings of the day,

Rakuen is now recruiting anime & manga fans!!

Looking for a place to watch, talk, and geek out over anime with people who get it? 👀✨
Join Rakuen Anime Club!
Whether you’re a newbie or a total otaku, everyone’s welcome — it’s all about having fun and making friends who share the same passion!

Register here - form

👉 Come vibe with us at Rakuen — your little slice of anime paradise 🌸✨

"""

# --- Classify the emails ---
results = classifier([email_1, email_2])
print("\n--- Classification Results ---")
for i, result in enumerate(results, 1):
    print(f"Email #{i}:")
    print(f"  Predicted Label: {result['label']}")
    print(f"  Confidence: {result['score']:.4f}\n")