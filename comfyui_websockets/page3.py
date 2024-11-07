import streamlit as st
import os
import subprocess
import requests
import json
import base64
from PIL import Image
import io


def base64_to_image(base64_string):
    """Base64 문자열을 PIL Image로 변환"""
    try:
        # Base64 문자열에서 헤더 제거
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(img_data))
    except Exception as e:
        st.error(f"Error converting base64 to image: {str(e)}")
        return None


def run():
    st.title('Image Segmentation')

    # File uploader for image
    uploaded_file = st.file_uploader("Upload an image", type=['png', 'jpg', 'jpeg'])

    # Text input for segmentation object
    segment_text = st.text_input('Enter the object to segment (e.g., "person", "car", "dog"):')

    # Debug output expander
    with st.expander("Debug Information", expanded=False):
        show_debug = st.checkbox("Show debug output")

    if uploaded_file is not None and segment_text and st.button('Run Segmentation'):
        with st.spinner('Processing image...'):
            try:
                # Save uploaded file temporarily
                temp_path = os.path.join("E:", "ComfyUI_windows_portable", "comfyui_websockets", "temp_upload.png")
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Show the original image
                st.write("Original Image:")
                st.image(temp_path)

                # Run the segmentation script
                api_script_path = os.path.join("E:", "ComfyUI_windows_portable", "comfyui_websockets",
                                               "segmentation_api2.py")
                result = subprocess.run(
                    ['python', api_script_path, temp_path, segment_text],
                    capture_output=True, text=True
                )

                if show_debug:
                    st.write("Script stdout:")
                    st.code(result.stdout)
                    st.write("Script stderr:")
                    st.code(result.stderr)

                if result.stderr:
                    st.error(f'Error occurred during processing: {result.stderr}')
                    return

                # Base64 출력 처리
                output_lines = result.stdout.strip().split('\n')
                base64_data = None

                # 마지막 줄이 Base64 데이터일 것으로 예상
                for line in reversed(output_lines):
                    if "data:image" in line or ";base64," in line:
                        base64_data = line.strip()
                        break

                if base64_data:
                    # Base64를 이미지로 변환
                    result_image = base64_to_image(base64_data)
                    if result_image:
                        st.write("Segmentation Result:")
                        st.image(result_image, caption="Segmented Image")

                        # Base64 데이터 다운로드 옵션 제공
                        st.download_button(
                            label="Download Segmented Image",
                            data=base64_data,
                            file_name="segmented_image.txt",
                            mime="text/plain"
                        )

                        st.success("Segmentation completed successfully!")
                    else:
                        st.error("Failed to convert Base64 to image")
                else:
                    st.error("No Base64 image data found in output")
                    if show_debug:
                        st.write("Full output:")
                        st.code(result.stdout)

                # Clean up the temporary upload file
                try:
                    os.remove(temp_path)
                except Exception as e:
                    st.error(f"Error removing temp file: {str(e)}")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    st.markdown("---")
    st.markdown("""
    ### Instructions:
    1. Upload an image you want to segment
    2. Enter the type of object you want to segment from the image
    3. Click 'Run Segmentation' to process

    The system will show both your original image and the segmented result.
    """)


if __name__ == "__main__":
    run()