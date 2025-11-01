from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib
import re

app = FastAPI()

# --- Training simple AI classifier ---
# --- Training simple AI classifier ---
train_texts = [
    "Music fest registrations open",
    "Drama auditions next week",
    "Hackathon event starting soon",
    "Paper presentation competition",
    "Art exhibition entry submission",
    "Coding contest 2025",
    "Campus recruitment drive",
    "Placement notice for final year students",
    "Company interview schedule",
    "Internship hiring process",
    "Student achievement award",
    "Best project recognition",
    "Scholarship won by student"
]
train_labels = ["cultural", "cultural", "technical", "technical", "cultural", "technical","placement", "placement",
    "placement", "placement", "achievements", "achievements", "achievements"]

vectorizer = TfidfVectorizer()
X_train = vectorizer.fit_transform(train_texts)
model = MultinomialNB()
model.fit(X_train, train_labels)

joblib.dump((vectorizer, model), "notice_classifier.pkl")
vectorizer, model = joblib.load("notice_classifier.pkl")

class NoticeInput(BaseModel):
    title: str = ""
    description: str = ""
    semester: str = ""
    
@app.post("/predict")
def predict_category(data: NoticeInput):
    combined_text = f"{data.title} {data.description}".strip()
    text_lower = combined_text.lower()
    semester =(data.semester).strip().lower()

    # --- Detect exam/semester keywords ---
    sem_match = re.search(r"sem\s*([1-8])", text_lower)
    # sem_match = re.search(r"(?:sem\s*|semester\s*)([1-8])", text_lower)
    sem_num = semester if semester else (sem_match.group(1) if sem_match else "")
    # if "exam" in text_lower and sem_num.isdigit():
    #     category = f"exam_sem{sem_num}"
    #     return {"category": category}
    # elif "exam" in text_lower:
    #     category = f"exam_{sem_num}"
    #     return {"category": category}
    if "exam" in combined_text:
    # IA detection
       if any(x in combined_text for x in ["ia", "internal", "midterm", "internal assessment"]):
        category = f"exam_ia{sem_num}" if sem_num else "exam_ia"
       else:
        category = f"exam_sem{sem_num}" if sem_num else "exam_sem"
       return {"category": category}


    # --- Try model prediction for non-exam notices ---
    try:
        X = vectorizer.transform([combined_text])
        category = model.predict(X)[0]
    except Exception:
        # --- Rule-based fallback ---
        if any(word in text_lower for word in ["placement", "recruitment", "campus drive", "job"]):
            category = "placement"
        elif any(word in text_lower for word in ["hackathon", "coding", "technical", "workshop", "competition"]):
            category = "technical"
        elif any(word in text_lower for word in ["music", "fest", "drama", "art", "dance", "cultural"]):
            category = "cultural"
        elif any(word in text_lower for word in ["award", "scholarship", "achievements", "recognition", "prize"]):
            category = "achievements"
        else:
            category = "general"

    # --- Ensure valid category ---
    if category not in ["technical", "cultural", "general"]:
        category = "general"

    return {"category": category}
# from fastapi import FastAPI
# from pydantic import BaseModel
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.naive_bayes import MultinomialNB
# import joblib
# import re
# import os

# app = FastAPI()

# # --- Train simple AI classifier once ---
# train_texts = [
#     "Music fest registrations open",
#     "Drama auditions next week",
#     "Hackathon event starting soon",
#     "Paper presentation competition",
#     "Art exhibition entry submission",
#     "Coding contest 2025",
#     "Campus recruitment drive",
#     "Placement notice for final year students",
#     "Company interview schedule",
#     "Internship hiring process",
#     "Student achievement award",
#     "Best project recognition",
#     "Scholarship won by student"
# ]

# train_labels = [
#     "cultural", "cultural", "technical", "technical", "cultural",
#     "technical", "placement", "placement", "placement", "placement",
#     "achievements", "achievements", "achievements"
# ]

# # Train only if model doesn't already exist
# MODEL_PATH = "notice_classifier.pkl"

# if not os.path.exists(MODEL_PATH):
#     vectorizer = TfidfVectorizer()
#     X_train = vectorizer.fit_transform(train_texts)
#     model = MultinomialNB()
#     model.fit(X_train, train_labels)
#     joblib.dump((vectorizer, model), MODEL_PATH)

# vectorizer, model = joblib.load(MODEL_PATH)


# # --- Input Schema ---
# class NoticeInput(BaseModel):
#     title: str = ""
#     description: str = ""
#     semester: str = ""


# # --- Prediction endpoint ---
# @app.post("/predict")
# def predict_category(data: NoticeInput):
#     combined_text = f"{data.title} {data.description}".strip().lower()
#     semester_text = data.semester.strip().lower()

#     # --- Detect exam-related categories first ---
#     sem_match = re.search(r"(?:sem\s*|semester\s*)([1-8])", combined_text)
#     sem_num = semester_text if semester_text.isdigit() else (sem_match.group(1) if sem_match else "")

#     if "exam" in combined_text:
#         # Internal Assessment detection
#         if any(x in combined_text for x in ["ia", "internal", "midterm", "internal assessment"]):
#             category = f"exam_ia{sem_num}" if sem_num else "exam_ia"
#         else:
#             category = f"exam_sem{sem_num}" if sem_num else "exam_sem"
#         return {"category": category}

#     # --- Use ML model for non-exam categories ---
#     try:
#         X = vectorizer.transform([combined_text])
#         category = model.predict(X)[0]
#     except Exception:
#         category = "general"

#     # --- Rule-based reinforcement ---
#     if any(word in combined_text for word in ["placement", "recruitment", "campus drive", "hiring", "offer", "job"]):
#         category = "placement"
#     elif any(word in combined_text for word in ["hackathon", "coding", "technical", "workshop", "competition"]):
#         category = "technical"
#     elif any(word in combined_text for word in ["music", "fest", "drama", "art", "dance", "cultural"]):
#         category = "cultural"
#     elif any(word in combined_text for word in ["award", "scholarship", "achievement", "recognition", "prize"]):
#         category = "achievements"

#     return {"category": category}
