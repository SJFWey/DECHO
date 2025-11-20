import streamlit as st
import os
import tempfile
import soundfile as sf
from backend.audio_processing import convert_to_wav
from backend.asr import transcribe_audio
from backend.nlp import split_sentences
from backend.subtitle import generate_srt
from backend.utils import setup_logging, load_config

# Initialize logging and config
setup_logging()
try:
    app_config = load_config()
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

st.set_page_config(page_title="Hearing App", layout="wide")

st.title("Hearing App - Local ASR & LLM")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    st.info("Using Local Parakeet Model & LLM")

    # Allow overriding max_split_length from sidebar
    default_max_len = app_config.get("app", {}).get("max_split_length", 80)
    max_split_length = st.number_input(
        "Max Split Length", min_value=20, max_value=500, value=default_max_len
    )
    app_config["app"]["max_split_length"] = max_split_length

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
                            " Audio is extremely short (< 0.1s). ASR might fail."
                        )
                    if info.samplerate != 16000:
                        st.warning(
                            " Sample rate is not 16000Hz. The ASR engine will attempt to resample, but this can introduce artifacts or errors."
                        )

                except Exception as e:
                    st.warning(f"Could not read audio metadata: {e}")

            except Exception as e:
                st.error(f"Conversion Failed: {e}")
                st.stop()

            # 2. ASR
            st.write("Running ASR...")
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

            # 3. NLP Splitting
            st.write("Splitting sentences...")
            try:
                if not full_text.strip():
                    st.warning("ASR produced empty text. Skipping splitting.")
                    final_segments = []
                else:
                    # Create a single initial segment using the total duration
                    duration = sf.info(wav_path).duration
                    initial_segments = [
                        {"text": full_text, "start": 0.0, "end": duration}
                    ]

                    final_segments = split_sentences(initial_segments, app_config)

                st.success(
                    f"Splitting Complete! Generated {len(final_segments)} segments."
                )

            except Exception as e:
                st.error(f"Splitting Failed: {e}")
                import traceback

                st.text(traceback.format_exc())
                st.stop()

            status.update(
                label="Processing Complete!", state="complete", expanded=False
            )

        # Display Results
        if "final_segments" in locals() and final_segments:
            # Generate SRT
            srt_content = generate_srt(final_segments)

            st.subheader("Generated Subtitles")

            st.text_area("SRT", srt_content, height=300)
            st.download_button(
                label="Download Subtitles (SRT)",
                data=srt_content,
                file_name="subtitles.srt",
                mime="text/plain",
            )
