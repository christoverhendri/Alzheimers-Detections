from flask import Flask, render_template, request, redirect, url_for, jsonify
from tensorflow.keras.models import load_model
import numpy as np
from tensorflow.keras.preprocessing import image
import os
from werkzeug.utils import secure_filename
import tensorflow as tf
import pandas as pd

# --- Config Flask ---
app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load model
model = tf.keras.models.load_model("alzheimer_model.h5")

# Class labels
class_names = ["MildDemented", "ModerateDemented", "NonDemented", "VeryMildDemented"]

# Load dataset
DATA_PATH = os.path.join("data", "alzheimers_data.csv")
if not os.path.exists(DATA_PATH):
    DATA_PATH = "alzheimers_data.csv"

df = pd.read_csv(DATA_PATH)


# ============================
#         ROUTES
# ============================

# HOME = route utama
@app.route('/')
def home():
    return render_template("home.html")


# UPLOAD / PREDICT PAGE (GET)
@app.route('/predict-page')
def predict_page():
    return render_template("index.html")


# DASHBOARD PAGE
@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")


# RESULT PAGE (POST)
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']

    if file.filename == '':
        return "No selected file"

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        # Preprocess image
        img = image.load_img(filepath, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        preds = model.predict(img_array)
        predicted_class = class_names[np.argmax(preds)]
        probability = float(np.max(preds))

        return render_template(
            'result.html',
            filename=filename,
            predicted_class=predicted_class,
            probability=round(probability * 100, 2)
        )

    return redirect(url_for('predict_page'))


# STATIC FILE (uploaded images)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename='uploads/' + filename))



# ============================
#         API ENDPOINTS
# ============================

@app.route('/api/summary')
def api_summary():
    total = len(df)

    if df['Diagnosis'].dtype in ['int64', 'float64']:
        counts = df['Diagnosis'].value_counts().to_dict()
        counts = {str(k): int(v) for k, v in counts.items()}
        perc_alz = round(100 * counts.get('1', 0) / total, 2)
    else:
        counts = df['Diagnosis'].value_counts().to_dict()
        perc_alz = None

    mean_age = round(df['Age'].mean(), 2)

    gender_counts = df['Gender'].value_counts().to_dict()
    male = gender_counts.get(1, 0)
    female = gender_counts.get(0, 0)
    total_g = male + female

    gender_male = round(100 * male / total_g, 2)
    gender_female = round(100 * female / total_g, 2)

    return jsonify({
        "total": total,
        "diagnosis_counts": counts,
        "percent_alzheimer": perc_alz,
        "mean_age": mean_age,
        "gender_male": gender_male,
        "gender_female": gender_female
    })


@app.route('/api/diagnosis_counts')
def api_diagnosis_counts():
    counts = df['Diagnosis'].value_counts().sort_index().to_dict()
    labels = [str(k) for k in counts.keys()]
    values = [int(v) for v in counts.values()]
    return jsonify({"labels": labels, "values": values})


@app.route('/api/age_distribution')
def api_age_distribution():
    ages = df['Age'].dropna().astype(int).tolist()
    bins = [50, 60, 70, 80, 90, 100]
    labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    counts = [0] * (len(bins) - 1)

    for a in ages:
        for i in range(len(bins) - 1):
            if bins[i] <= a < bins[i+1]:
                counts[i] += 1
                break

    return jsonify({"labels": labels, "counts": counts})


@app.route('/api/bmi_stats')
def api_bmi_stats():
    res = {}
    for diag, g in df.groupby('Diagnosis'):
        arr = g['BMI'].dropna().astype(float)
        res[str(int(diag))] = {
            "count": int(len(arr)),
            "mean": round(float(arr.mean()), 2),
            "std": round(float(arr.std()), 2),
            "min": round(float(arr.min()), 2),
            "q1": round(float(arr.quantile(0.25)), 2),
            "median": round(float(arr.median()), 2),
            "q3": round(float(arr.quantile(0.75)), 2),
            "max": round(float(arr.max()), 2)
        }
    return jsonify(res)


@app.route('/api/education_vs_diagnosis')
def api_education_vs_diagnosis():
    pivot = df.groupby(['EducationLevel', 'Diagnosis']).size().unstack(fill_value=0)
    labels = pivot.index.astype(str).tolist()
    dataset0 = pivot.get(0, pd.Series([0]*len(labels))).tolist()
    dataset1 = pivot.get(1, pd.Series([0]*len(labels))).tolist()
    return jsonify({"labels": labels, "no_dementia": dataset0, "dementia": dataset1})


@app.route('/api/smoking_by_diag')
def api_smoking_by_diag():
    pivot = df.groupby('Diagnosis')['Smoking'].mean().to_dict()
    return jsonify({str(int(k)): round(float(v), 3) for k, v in pivot.items()})


@app.route('/api/alcohol_stats')
def api_alcohol_stats():
    res = {}
    for diag, g in df.groupby('Diagnosis'):
        arr = g['AlcoholConsumption'].dropna().astype(float)
        res[str(int(diag))] = {
            "median": round(float(arr.median()), 2),
            "q1": round(float(arr.quantile(0.25)), 2),
            "q3": round(float(arr.quantile(0.75)), 2),
            "mean": round(float(arr.mean()), 2)
        }
    return jsonify(res)


@app.route('/api/activity_by_diag')
def api_activity_by_diag():
    pivot = df.groupby('Diagnosis')['PhysicalActivity'].mean().to_dict()
    return jsonify({str(int(k)): round(float(v), 3) for k, v in pivot.items()})



@app.route('/api/cognitive_stats')
def api_cognitive_stats():
    res = {}
    key_features = ['MMSE','MemoryComplaints','BehavioralProblems','Confusion',
                    'Disorientation','Forgetfulness','DifficultyCompletingTasks','ADL']
    for diag, g in df.groupby('Diagnosis'):
        stats = {}
        for f in key_features:
            arr = g[f].dropna().astype(float)
            stats[f] = {
                "mean": round(float(arr.mean()), 2),
                "q1": round(float(arr.quantile(0.25)), 2),
                "median": round(float(arr.median()), 2),
                "q3": round(float(arr.quantile(0.75)), 2)
            }
        res[str(int(diag))] = stats
    return jsonify(res)


@app.route('/api/radar_data')
def api_radar_data():
    features = ['MemoryComplaints', 'BehavioralProblems', 'Disorientation', 'Confusion',
                'Forgetfulness', 'DifficultyCompletingTasks', 'PersonalityChanges',
                'EmotionalDistress' if 'EmotionalDistress' in df.columns else 'ADL']
    data = {"labels": features, "datasets": []}
    for diag, g in df.groupby('Diagnosis'):
        means = [round(float(g[f].mean()), 2) if f in g.columns else 0 for f in features]
        data["datasets"].append({"label": str(int(diag)), "data": means})
    return jsonify(data)


@app.route('/api/correlation_diagnosis')
def api_corr_diag():
    numeric = df.select_dtypes(include=['number'])
    corr = numeric.corr()['Diagnosis'].drop('Diagnosis')
    corr = corr.sort_values(ascending=False).round(3)
    return jsonify({"features": corr.index.tolist(), "values": corr.tolist()})


# ============================
# RUN
# ============================
if __name__ == '__main__':
    app.run(debug=True)
