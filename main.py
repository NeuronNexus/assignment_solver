from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
import os
import zipfile
import pandas as pd
import json
from rapidfuzz import process  # Import rapidfuzz for string similarity
import re  # Import re for text normalization

app = FastAPI()

# Function to normalize text
def normalize_text(text):
    text = text.lower()  # Convert to lowercase
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces/newlines with a single space
    text = re.sub(r'[^\w\s\-\.\,]', '', text)  # Remove all punctuation except -, ., and ,
    return text.strip()

# Function to load questions and answers from multiple assignment folders
def load_assignments(*folder_paths):
    assignments = {}
    for folder_path in folder_paths:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.startswith("q") and file.endswith(".txt") or file.endswith(".md"):
                    question_path = os.path.join(root, file)
                    solution_path = question_path.replace("q", "sol")
                    if os.path.exists(solution_path):
                        with open(question_path, "r", encoding="utf-8") as qf:
                            question = normalize_text(qf.read().strip())  # Normalize question
                        with open(solution_path, "r", encoding="utf-8") as sf:
                            if solution_path.endswith(".sh"):
                                answer = sf.read().strip()  # Read shell script content as answer
                            else:
                                answer = sf.read().strip()
                        assignments[question] = answer
    print(f"Loaded assignments: {assignments}")  # Debug: Log loaded assignments
    return assignments

# Load assignments from both folders
assignments = load_assignments("assignment", "assignment 2")

@app.post("/api/")
async def answer_question(
    question: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        # Normalize the input question
        normalized_question = normalize_text(question)

        # Debug: Log the normalized input question
        print(f"Normalized input question: {normalized_question}")

        # Find the closest question using rapidfuzz
        result = process.extractOne(normalized_question, assignments.keys())
        if not result:
            return JSONResponse(content={"answer": "No closely matching question found."})
        
        closest_question, similarity = result[0], result[1]  # Extract question and similarity score

        # Debug: Log the closest question and similarity score
        print(f"Closest question: {closest_question}, Similarity: {similarity}")

        if similarity < 70:  # Increased threshold for similarity
            return JSONResponse(content={"answer": "No closely matching question found."})

        # Handle numerical operations or file-based questions
        if file:
            file_path = f"temp/{file.filename}"
            with open(file_path, "wb") as f:
                f.write(await file.read())

            if file.filename.endswith(".zip"):
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall("temp/")

                # Example: Process CSV file
                csv_file = [f for f in os.listdir("temp/") if f.endswith(".csv")][0]
                df = pd.read_csv(f"temp/{csv_file}")
                answer = df["answer"].iloc[0]  # Example logic
            else:
                answer = "File type not supported."
        else:
            # Extract answer from the closest question
            answer = assignments.get(closest_question, "Answer not found.")

        # Debug: Log the final answer
        print(f"Final answer: {answer}")

        return JSONResponse(content={"answer": answer})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
