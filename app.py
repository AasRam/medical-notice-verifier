import streamlit as st
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_bytes
import re
from datetime import datetime

# Optional Google Vision (safe)
try:
    from google.cloud import vision
    GOOGLE_AVAILABLE = True
except:
    GOOGLE_AVAILABLE = False


# -------------------- UI --------------------
st.set_page_config(page_title="Medical Notice Verifier", layout="centered")
st.title("🏥 Student Medical Notice Verifier")

st.write("Upload a medical notice (PDF / Image) to verify its authenticity.")

uploaded_file = st.file_uploader(
    "📤 Upload Medical Notice",
    type=["jpg", "png", "pdf"]
)

# -------------------- FUNCTIONS --------------------
def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)
    return thresh


def extract_text_google(image_np):
    try:
        client = vision.ImageAnnotatorClient()
        _, encoded = cv2.imencode(".png", image_np)
        content = encoded.tobytes()
        image = vision.Image(content=content)
        response = client.text_detection(image=image)

        if response.text_annotations:
            return response.text_annotations[0].description, "Google Vision API"
    except:
        pass

    return None, None


def extract_text_tesseract(image_np):
    return pytesseract.image_to_string(image_np), "Tesseract OCR"


def extract_text(image_np):
    if GOOGLE_AVAILABLE:
        text, engine = extract_text_google(image_np)
        if text:
            return text, engine

    return extract_text_tesseract(image_np)


def basic_validation(text):
    score = 0
    reasons = []

    if re.search(r"hospital|clinic|medical", text, re.IGNORECASE):
        score += 1
    else:
        reasons.append("Hospital/Clinic name not found")

    if re.search(r"Dr\.", text):
        score += 1
    else:
        reasons.append("Doctor name not found")

    if re.search(r"[A-Z]{2}/\d{3,6}/\d{4}", text):
        score += 1
    else:
        reasons.append("Doctor registration number missing")

    dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)
    if dates:
        try:
            doc_date = datetime.strptime(dates[0], "%d/%m/%Y")
            if doc_date <= datetime.now():
                score += 1
            else:
                reasons.append("Date is in the future")
        except ValueError:
            reasons.append("Invalid date format")
    else:
        reasons.append("Date not found")

    return score, reasons


# -------------------- PROCESSING --------------------
image_np = None

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        images = convert_from_bytes(uploaded_file.read())
        image_np = np.array(images[0])
    else:
        image_np = np.array(Image.open(uploaded_file))

if image_np is not None:
    processed = preprocess_image(image_np)
    text, engine = extract_text(processed)

    st.subheader("🔍 OCR Engine Used")
    st.info(engine)

    st.subheader("📄 Extracted Text")
    st.text(text)

    score, reasons = basic_validation(text)

    st.subheader("✅ Verification Result")
    if score >= 3:
        st.success("✔ Acceptable for Academic Use")
    elif score == 2:
        st.warning("⚠ Needs Manual Verification")
    else:
        st.error("❌ Likely Invalid")

    if reasons:
        st.subheader("⚠ Issues Found")
        for r in reasons:
            st.write("- ", r)


