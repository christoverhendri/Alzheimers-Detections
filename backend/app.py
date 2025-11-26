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

# ========== PRE-COMPUTE DASHBOARD DATA FOR FASTER API RESPONSE ==========
print("[STARTUP] Pre-computing dashboard data...")

# Summary stats
total_patients = len(df)
diagnosis_counts = df['Diagnosis'].value_counts().to_dict()
mean_age = float(df['Age'].mean())
gender_counts = df['Gender'].value_counts().to_dict()
male_pct = round(100 * gender_counts.get(1, 0) / len(df), 2)
female_pct = round(100 * gender_counts.get(0, 0) / len(df), 2)

# Age distribution
ages = df['Age'].dropna().astype(int).tolist()
age_bins = [50, 60, 70, 80, 90, 100]
age_labels = [f"{age_bins[i]}-{age_bins[i+1]-1}" for i in range(len(age_bins)-1)]
age_counts = [0]*(len(age_bins)-1)
for a in ages:
    for i in range(len(age_bins)-1):
        if age_bins[i] <= a < age_bins[i+1]:
            age_counts[i] += 1
            break

# BMI stats
bmi_stats = {}
for diag, g in df.groupby("Diagnosis"):
    arr = g["BMI"].dropna().astype(float)
    bmi_stats[str(int(diag))] = {
        "count": len(arr),
        "mean": round(arr.mean(), 2),
        "std": round(arr.std(), 2),
        "min": round(arr.min(), 2),
        "q1": round(arr.quantile(0.25), 2),
        "median": round(arr.median(), 2),
        "q3": round(arr.quantile(0.75), 2),
        "max": round(arr.max(), 2)
    }

# Smoking
smoking_data = {}
for diag, g in df.groupby("Diagnosis"):
    smoking_data[str(int(diag))] = round(float(g["Smoking"].mean()), 3)

# Alcohol
alcohol_stats = {}
for diag, g in df.groupby("Diagnosis"):
    arr = g["AlcoholConsumption"].dropna().astype(float)
    alcohol_stats[str(int(diag))] = {
        "median": round(arr.median(), 2),
        "q1": round(arr.quantile(0.25), 2),
        "q3": round(arr.quantile(0.75), 2),
        "mean": round(arr.mean(), 2),
    }

# Activity
activity_data = {}
for diag, g in df.groupby("Diagnosis"):
    activity_data[str(int(diag))] = round(float(g["PhysicalActivity"].mean()), 3)

# Cognitive
cognitive_stats = {}
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
    cognitive_stats[str(int(diag))] = stats

# Radar
radar_features = ['MemoryComplaints', 'BehavioralProblems', 'Disorientation',
                  'Confusion', 'Forgetfulness', 'DifficultyCompletingTasks',
                  'PersonalityChanges', 'ADL']
radar_data = {"labels": radar_features, "datasets": []}
for diag, g in df.groupby("Diagnosis"):
    means = [round(float(g[f].mean()), 2) if f in g.columns else 0 for f in radar_features]
    radar_data["datasets"].append({"label": str(int(diag)), "data": means})

# Correlation
numeric = df.select_dtypes(include=['number'])
corr = numeric.corr()['Diagnosis'].drop('Diagnosis').sort_values(ascending=False)
corr_data = {"features": corr.index.tolist(), "values": corr.round(3).tolist()}

# Education vs Diagnosis
edu_pivot = df.groupby(['EducationLevel', 'Diagnosis']).size().unstack(fill_value=0)
edu_labels = edu_pivot.index.astype(str).tolist()
edu_no_dementia = edu_pivot.get(0, pd.Series([0]*len(edu_labels))).tolist()
edu_dementia = edu_pivot.get(1, pd.Series([0]*len(edu_labels))).tolist()

print("[STARTUP] Pre-computation complete!")

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
    return jsonify({
        "total": total_patients,
        "diagnosis_counts": {str(k): int(v) for k, v in diagnosis_counts.items()},
        "percent_alzheimer": round(100 * diagnosis_counts.get(1, 0) / total_patients, 2),
        "mean_age": round(mean_age, 2),
        "gender_male": male_pct,
        "gender_female": female_pct
    })

@app.route('/api/diagnosis_counts')
def api_diagnosis_counts():
    return jsonify({
        "labels": [str(k) for k in sorted(diagnosis_counts.keys())],
        "values": [diagnosis_counts[k] for k in sorted(diagnosis_counts.keys())]
    })

@app.route('/api/age_distribution')
def api_age_distribution():
    return jsonify({"labels": age_labels, "counts": age_counts})

@app.route('/api/bmi_stats')
def api_bmi_stats():
    return jsonify(bmi_stats)

@app.route('/api/education_vs_diagnosis')
def api_education_vs_diagnosis():
    return jsonify({
        "labels": edu_labels,
        "no_dementia": edu_no_dementia,
        "dementia": edu_dementia,
    })

@app.route('/api/smoking_by_diag')
def api_smoking_by_diag():
    return jsonify(smoking_data)

@app.route('/api/alcohol_stats')
def api_alcohol_stats():
    return jsonify(alcohol_stats)

@app.route('/api/activity_by_diag')
def api_activity_by_diag():
    return jsonify(activity_data)

@app.route('/api/cognitive_stats')
def api_cognitive_stats():
    return jsonify(cognitive_stats)

@app.route('/api/radar_data')
def api_radar():
    return jsonify(radar_data)

@app.route('/api/correlation_diagnosis')
def api_corr():
    return jsonify(corr_data)

# ---------------------------------------------------
# RUN SERVER
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
