import streamlit as st
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_bytes
import re
from datetime import datetime

st.title("🏥 Student Medical Notice Verifier")

mode = st.radio(
    "Choose input method:",
    ("Upload File", "Scan Using Camera")
)




def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)
    return thresh


def extract_text_from_image(image):
    return pytesseract.image_to_string(image)


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
        except:
            reasons.append("Invalid date format")
    else:
        reasons.append("Date not found")

    return score, reasons


image_np = None

# ===== UPLOAD MODE =====
if mode == "Upload File":
    uploaded_file = st.file_uploader(
        "Upload a medical notice (JPG, PNG, or PDF)",
        type=["jpg", "png", "pdf"]
    )

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            images = convert_from_bytes(uploaded_file.read())
            image_np = np.array(images[0])
        else:
            image_np = np.array(Image.open(uploaded_file))


# ===== CAMERA MODE =====
elif mode == "Scan Using Camera":
    camera_image = st.camera_input("Take a photo of the medical notice")

    if camera_image:
        image = Image.open(camera_image)
        image_np = np.array(image)


# ===== COMMON PROCESSING =====
if image_np is not None:
    processed = preprocess_image(image_np)
    text = extract_text_from_image(processed)

    st.subheader("📄 Extracted Text")
    st.text(text)

    score, reasons = basic_validation(text)

    st.subheader("✅ Result")
    if score >= 3:
        st.success("✔ Acceptable for Academic Use")
    elif score == 2:
        st.warning("⚠ Needs Manual Verification")
    else:
        st.error("❌ Likely Invalid")

    if reasons:
        st.subheader("⚠ Issues")
        for r in reasons:
            st.write("- ", r)


