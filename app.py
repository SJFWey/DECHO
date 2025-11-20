import streamlit as st
import os
import tempfile
import soundfile as sf
from backend.audio_processing import convert_to_wav
from backend.asr import transcribe_audio
from backend.llm import split_text_by_meaning
import json

st.set_page_config(page_title="Hearing App", layout="wide")

st.title("Hearing App - Local ASR & LLM")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    st.info("Using Local Parakeet Model & LLM")

# File Upload
uploaded_file = st.file_uploader("Upload Audio File", type=["mp3", "wav", "m4a", "mp4"])

if uploaded_file:
    # Save uploaded file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        input_path = tmp_file.name

    st.audio(input_path)

    if st.button("Start Processing"):
        with st.status("Processing...", expanded=True) as status:
            # 1. Convert Audio
            st.write("Converting audio...")
            try:
                wav_path = convert_to_wav(input_path)

                # Diagnostics for the converted file
                try:
                    info = sf.info(wav_path)
                    st.info(
                        f"**Audio Diagnostics:**\n"
                        f"- Sample Rate: {info.samplerate} Hz\n"
                        f"- Channels: {info.channels}\n"
                        f"- Duration: {info.duration:.2f} s\n"
                        f"- Format: {info.format}\n"
                        f"- Subtype: {info.subtype}"
                    )

                    if info.duration < 0.1:
                        st.warning(
                            "⚠️ Audio is extremely short (< 0.1s). ASR might fail."
                        )
                    if info.samplerate != 16000:
                        st.warning(
                            "⚠️ Sample rate is not 16000Hz. The ASR engine will attempt to resample, but this can introduce artifacts or errors."
                        )

                except Exception as e:
                    st.warning(f"Could not read audio metadata: {e}")

            except Exception as e:
                st.error(f"Conversion Failed: {e}")
                st.stop()

            # 2. ASR
            st.write("Running ASR (Locally using Parakeet V3)...")
            try:
                asr_result = transcribe_audio(wav_path)
                # Handle result format
                if isinstance(asr_result, dict):
                    full_text = asr_result.get("text", "")
                    timestamps = asr_result.get("timestamps", [])
                else:
                    # Fallback if result is just text or other object
                    full_text = str(asr_result)
                    timestamps = []

                st.success("ASR Complete!")
                st.text_area("Raw Transcript", full_text, height=150)
            except Exception as e:
                st.error(f"ASR Failed: {e}")

                st.markdown("---")
                st.error("### Troubleshooting Analysis")
                st.markdown(f""" **Error Details:** `{str(e)}` """)
                st.stop()

            # 3. NLP/LLM Splitting
            st.write("Splitting sentences...")
            try:
                # If we have timestamps, we might want to align them, but for now let's just split the text
                # Ideally we would use the timestamps to split the audio, but here we just split text for display

                # If the text is very long, we might need to chunk it for LLM
                if not full_text.strip():
                    st.warning("ASR produced empty text. Skipping LLM splitting.")
                    segments = []
                else:
                    segments = split_text_by_meaning(full_text)
                    st.success("Splitting Complete!")
            except Exception as e:
                st.error(f"LLM Splitting Failed: {e}")
                segments = [full_text]

            status.update(
                label="Processing Complete!", state="complete", expanded=False
            )

        # Display Results
        if segments:
            # Export options
            st.download_button(
                label="Download Subtitles (JSON)",
                data=json.dumps(segments, indent=2, ensure_ascii=False),
                file_name="subtitles.json",
                mime="application/json",
            )
        else:
            st.info("Output error, please check the input or try again.")
