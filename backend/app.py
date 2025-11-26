from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import os
import pandas as pd
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
app = Flask(__name__)
CORS(app)  # Allow frontend (5500) to access backend API

UPLOAD_FOLDER = "../frontend/static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Load model
model = tf.keras.models.load_model("alzheimer_model.h5")

# Labels
class_names = ["MildDemented", "ModerateDemented", "NonDemented", "VeryMildDemented"]

# Load dataset
DATA_PATH = os.path.join("data", "alzheimers_data.csv")
df = pd.read_csv(DATA_PATH)

# ---------------------------------------------------
# PREDICTION API
# ---------------------------------------------------
@app.route("/api/predict", methods=["POST"])
def predict_api():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(filepath)

    img = image.load_img(filepath, target_size=(224, 224))
    img_array = np.expand_dims(image.img_to_array(img) / 255.0, 0)

    preds = model.predict(img_array)
    predicted_class = class_names[np.argmax(preds)]
    prob = float(np.max(preds))

    return jsonify({
        "filename": filename,
        "predicted_class": predicted_class,
        "probability": round(prob * 100, 2)
    })

# ---------------------------------------------------
# ALL API ROUTES FOR DASHBOARD
# ---------------------------------------------------
@app.route('/api/summary')
def api_summary():
    total = len(df)
    counts = df['Diagnosis'].value_counts().to_dict()
    counts = {str(k): int(v) for k, v in counts.items()}

    mean_age = float(df['Age'].mean())

    gender_counts = df['Gender'].value_counts().to_dict()
    male = gender_counts.get(1, 0)
    female = gender_counts.get(0, 0)
    total_g = male + female

    return jsonify({
        "total": total,
        "diagnosis_counts": counts,
        "percent_alzheimer": round(100 * counts.get("1", 0) / total, 2),
        "mean_age": round(mean_age, 2),
        "gender_male": round(100 * male / total_g, 2),
        "gender_female": round(100 * female / total_g, 2)
    })

@app.route('/api/diagnosis_counts')
def api_diagnosis_counts():
    counts = df['Diagnosis'].value_counts().sort_index().to_dict()
    return jsonify({
        "labels": list(map(str, counts.keys())),
        "values": list(counts.values())
    })

@app.route('/api/age_distribution')
def api_age_distribution():
    ages = df['Age'].dropna().astype(int).tolist()
    bins = [50, 60, 70, 80, 90, 100]
    labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    counts = [0]*(len(bins)-1)

    for a in ages:
        for i in range(len(bins)-1):
            if bins[i] <= a < bins[i+1]:
                counts[i] += 1
                break
    return jsonify({"labels": labels, "counts": counts})

@app.route('/api/bmi_stats')
def api_bmi_stats():
    res = {}
    for diag, g in df.groupby("Diagnosis"):
        arr = g["BMI"].dropna().astype(float)
        res[str(int(diag))] = {
            "count": len(arr),
            "mean": round(arr.mean(), 2),
            "std": round(arr.std(), 2),
            "min": round(arr.min(), 2),
            "q1": round(arr.quantile(0.25), 2),
            "median": round(arr.median(), 2),
            "q3": round(arr.quantile(0.75), 2),
            "max": round(arr.max(), 2)
        }
    return jsonify(res)

@app.route('/api/education_vs_diagnosis')
def api_education_vs_diagnosis():
    pivot = df.groupby(['EducationLevel', 'Diagnosis']).size().unstack(fill_value=0)
    labels = pivot.index.astype(str).tolist()
    dataset0 = pivot.get(0, pd.Series([0]*len(labels))).tolist()
    dataset1 = pivot.get(1, pd.Series([0]*len(labels))).tolist()
    return jsonify({
        "labels": labels,
        "no_dementia": dataset0,
        "dementia": dataset1,
    })

@app.route('/api/smoking_by_diag')
def api_smoking_by_diag():
    pivot = df.groupby("Diagnosis")["Smoking"].mean().to_dict()
    return jsonify({str(int(k)): round(float(v), 3) for k, v in pivot.items()})

@app.route('/api/alcohol_stats')
def api_alcohol_stats():
    res = {}
    for diag, g in df.groupby("Diagnosis"):
        arr = g["AlcoholConsumption"].dropna().astype(float)
        res[str(int(diag))] = {
            "median": round(arr.median(), 2),
            "q1": round(arr.quantile(0.25), 2),
            "q3": round(arr.quantile(0.75), 2),
            "mean": round(arr.mean(), 2),
        }
    return jsonify(res)

@app.route('/api/activity_by_diag')
def api_activity_by_diag():
    pivot = df.groupby("Diagnosis")["PhysicalActivity"].mean().to_dict()
    return jsonify({str(int(k)): round(float(v), 3) for k, v in pivot.items()})

@app.route('/api/cognitive_stats')
def api_cognitive_stats():
    res = {}
    feats = ['MMSE','MemoryComplaints','BehavioralProblems','Confusion',
             'Disorientation','Forgetfulness','DifficultyCompletingTasks','ADL']
    for diag, g in df.groupby("Diagnosis"):
        stats = {}
        for f in feats:
            arr = g[f].dropna().astype(float)
            stats[f] = {
                "mean": round(arr.mean(), 2),
                "q1": round(arr.quantile(0.25), 2),
                "median": round(arr.median(), 2),
                "q3": round(arr.quantile(0.75), 2),
            }
        res[str(int(diag))] = stats
    return jsonify(res)

@app.route('/api/radar_data')
def api_radar():
    features = ['MemoryComplaints', 'BehavioralProblems', 'Disorientation',
                'Confusion', 'Forgetfulness', 'DifficultyCompletingTasks',
                'PersonalityChanges',
                'EmotionalDistress' if 'EmotionalDistress' in df.columns else 'ADL']
    data = {"labels": features, "datasets": []}
    for diag, g in df.groupby("Diagnosis"):
        means = [round(float(g[f].mean()), 2) if f in g.columns else 0 for f in features]
        data["datasets"].append({"label": str(int(diag)), "data": means})
    return jsonify(data)

@app.route('/api/correlation_diagnosis')
def api_corr():
    numeric = df.select_dtypes(include=['number'])
    corr = numeric.corr()['Diagnosis'].drop('Diagnosis').sort_values(ascending=False)
    return jsonify({"features": corr.index.tolist(), "values": corr.round(3).tolist()})

# ---------------------------------------------------
# RUN SERVER
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
