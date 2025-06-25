from flask import Flask, render_template, request, send_file
from fpdf import FPDF
import numpy as np
import pickle
import os
import time
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Load trained model
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

# Unicode-safe sanitize function
def sanitize(text):
    return text.replace("–", "-").replace("—", "-").replace("“", "\"").replace("”", "\"").encode('latin-1', 'ignore').decode('latin-1')

# Extract values from uploaded PDF
def extract_values_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()

        def extract_number(keyword):
            for line in text.splitlines():
                if keyword.lower() in line.lower():
                    for part in line.split():
                        try:
                            return float(part)
                        except:
                            continue
            return None

        hb = extract_number("Hemoglobin")
        wbc = extract_number("WBC")
        ecg = extract_number("ECG")
        return hb, wbc, ecg
    except Exception as e:
        print("Error reading PDF:", e)
        return None, None, None

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/predict', methods=['POST'])
def predict():
    use_pdf = request.form.get('use_pdf')

    if use_pdf == 'yes':
        file = request.files['report_file']
        if not file or file.filename == '':
            return "No PDF file uploaded", 400

        os.makedirs("uploads", exist_ok=True)
        filename = f"{int(time.time())}_{secure_filename(file.filename)}"
        upload_path = os.path.join("uploads", filename)
        file.save(upload_path)

        hb, wbc, ecg = extract_values_from_pdf(upload_path)
    else:
        try:
            hb = float(request.form['hemoglobin'])
            wbc = float(request.form['wbc'])
            ecg = float(request.form['ecg'])
        except ValueError:
            return "Please enter valid numeric values", 400

    # Validate inputs
    if None in [hb, wbc, ecg]:
        return "Failed to extract required values. Check input or PDF content.", 400

    # Make prediction
    input_data = np.array([[hb, wbc, ecg]])
    prediction = model.predict(input_data)[0]
    result = "Blood Cancer Detected" if prediction == 1 else "Normal"

    # Generate PDF report
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=sanitize("Blood Cancer Prediction Report"), ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=sanitize(f"Hemoglobin: {hb} g/dL"), ln=True)
    pdf.cell(200, 10, txt=sanitize(f"WBC Count: {wbc} cells/μL"), ln=True)
    pdf.cell(200, 10, txt=sanitize(f"ECG Heart Rate: {ecg} bpm"), ln=True)
    pdf.cell(200, 10, txt=sanitize(f"Prediction: {result}"), ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=sanitize("Reference Normal Ranges:"), ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=sanitize("- Hemoglobin: 13.5 - 17.5 g/dL"), ln=True)
    pdf.cell(200, 10, txt=sanitize("- WBC Count: 4,500 - 11,000 cells/μL"), ln=True)
    pdf.cell(200, 10, txt=sanitize("- ECG Heart Rate: 60 - 100 bpm"), ln=True)

    os.makedirs("report", exist_ok=True)
    report_path = "report/report.pdf"
    pdf.output(report_path)

    return render_template("index.html", prediction=result, show_pdf=True)

@app.route('/download')
def download():
    return send_file("report/report.pdf", as_attachment=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
