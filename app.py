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


# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Medical Notice Verifier", layout="centered")

# -------------------- CUSTOM STYLING --------------------
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #f0f4ff, #ffffff);
}
.main {
    background-color: #ffffff;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.05);
}
h1 {
    color: #2c3e50;
}
</style>
""", unsafe_allow_html=True)

# -------------------- UI --------------------
st.title("🏥 Student Medical Notice Verifier")
st.write("Select one method, upload or scan the medical notice, then click **Verify**.")

# 🔽 Dropdown (user must choose one)
mode = st.selectbox(
    "📌 Select Input Method",
    ["Upload Medical Notice", "Scan Using Camera"]
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
    issues = []

    if not re.search(r"hospital|clinic|medical", text, re.IGNORECASE):
        issues.append("Hospital / Clinic name not found")

    if not re.search(r"Dr\.", text):
        issues.append("Doctor name not found")

    if not re.search(r"[A-Z]{2}/\d{3,6}/\d{4}", text):
        issues.append("Doctor registration number missing")

    dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)
    if dates:
        try:
            if datetime.strptime(dates[0], "%d/%m/%Y") > datetime.now():
                issues.append("Date is in the future")
        except ValueError:
            issues.append("Invalid date format")
    else:
        issues.append("Date not found")

    return issues


# -------------------- INPUT HANDLING --------------------
image_np = None

if mode == "Upload Medical Notice":
    uploaded_file = st.file_uploader(
        "📤 Upload Medical Notice (PDF / Image)",
        type=["jpg", "png", "pdf"]
    )

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            images = convert_from_bytes(uploaded_file.read())
            image_np = np.array(images[0])
        else:
            image_np = np.array(Image.open(uploaded_file))

elif mode == "Scan Using Camera":
    camera_image = st.camera_input("📷 Scan Medical Notice")

    if camera_image:
        image_np = np.array(Image.open(camera_image))


# -------------------- ACTION BUTTON --------------------
st.markdown("---")
verify_clicked = st.button("🔍 Verify Medical Notice")

# -------------------- PROCESSING (ONLY ON CLICK) --------------------
if verify_clicked:
    if image_np is None:
        st.warning("⚠ Please upload or scan a medical notice first.")
    else:
        processed = preprocess_image(image_np)
        text, engine = extract_text(processed)

        st.subheader("🔍 OCR Engine Used")
        st.info(engine)

        st.subheader("📄 Extracted Text")
        st.text(text)

        issues = basic_validation(text)

        st.subheader("✅ Verification Result")
        if not issues:
            st.success("✔ Accepted – Medical Notice is Valid")
        else:
            st.error("❌ Not Accepted – Medical Notice is Invalid")
            st.subheader("⚠ Issues Found")
            for issue in issues:
                st.write("•", issue)



