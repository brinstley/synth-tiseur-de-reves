import streamlit as st
import datetime
import json
from pathlib import Path
import whisper
import tempfile
import os
import requests
from PIL import Image
from io import BytesIO
import google.generativeai as genai

# Configuration de la page
st.set_page_config(page_title="Synthétiseur de Rêves", layout="centered")
st.title("🌙 Synthétiseur de Rêves")
st.markdown("Bienvenue ! Racontez-nous votre rêve...")

# Chargement des rêves enregistrés
def load_dreams():
    file = Path("dreams.json")
    if file.exists():
        try:
            with open(file, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []

# Sauvegarde d'un rêve
def save_dream(dream):
    dreams = load_dreams()
    dreams.append(dream)
    with open("dreams.json", "w") as f:
        json.dump(dreams, f, indent=2)

# Upload d’un fichier audio
uploaded_file = st.file_uploader("📤 Uploader un fichier audio (.wav uniquement)", type=["wav"])

if uploaded_file is not None:
    st.audio(uploaded_file)
    st.success("Audio uploadé avec succès !")

    # Sauvegarde temporaire du fichier
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name

    # Transcription locale avec Whisper (sans ffmpeg car .wav = direct)
    st.info("⏳ Transcription en cours avec Whisper...")
    try:
        model = whisper.load_model("base")
        result = model.transcribe(tmp_file_path)
        transcribed_text = result["text"]
        st.text_area("📝 Texte du rêve :", transcribed_text, height=150)
    except Exception as e:
        st.error(f"❌ Échec de la transcription audio : {e}")
        st.stop()

    # Analyse émotionnelle avec Gemini
    st.info("🔍 Analyse émotionnelle avec Gemini...")
    genai.configure(api_key=st.secrets["gemini_api_key"])

    emotion_prompt = f"""
    Tu es un détecteur d’émotion. Lis ce rêve et réponds uniquement par une émotion dominante : heureux, triste, stressant, angoissé, émerveillé, neutre, etc.

    Rêve :
    \"\"\"{transcribed_text}\"\"\"

    Réponds uniquement par l'émotion. Pas d'explication.
    """
    model_gemini = genai.GenerativeModel("gemini-1.5-flash")
    response = model_gemini.generate_content(emotion_prompt)
    emotion = response.text.strip()
    st.success(f"🎭 Émotion détectée : {emotion}")

    # Génération d’image via ClipDrop
    st.info("🎨 Génération de l’image avec ClipDrop…")
    headers = {
        "x-api-key": st.secrets["clipdrop_api_key"],
        "Content-Type": "application/json"
    }
    data = {
        "prompt": transcribed_text
    }

    response = requests.post(
        "https://clipdrop-api.co/text-to-image/v1",
        headers=headers,
        json=data,
    )

    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        st.image(image, caption="🌠 Image générée à partir du rêve")

        # Sauvegarde du rêve
        dream_data = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "text": transcribed_text,
            "emotion": emotion,
            "image_url": ""
        }
        save_dream(dream_data)
    else:
        st.error("❌ Échec de la génération d'image : " + response.text)

# Historique des rêves
if st.checkbox("📜 Voir mes anciens rêves"):
    dreams = load_dreams()
    for dream in dreams:
        st.write(f"🗓️ {dream['date']}")
        st.write(f"💬 {dream['text']}")
        st.write(f"🎭 Émotion : {dream['emotion']}")
        if dream.get("image_url"):
            st.image(dream["image_url"])
        st.markdown("---")
