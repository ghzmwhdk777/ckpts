import streamlit as st
import os
import subprocess


def run():
    st.title('Image Segmentation')

    # File uploader for image
    uploaded_file = st.file_uploader("Upload an image", type=['png', 'jpg', 'jpeg'])

    # Text input for segmentation object
    segment_text = st.text_input('Segment할 객체를 영어로 써주세요 (e.g., "person", "car", "dog"):')

    # Add a description
    st.markdown("""
    당신이 업로드한 이미지를 segmentation해줍니다. 
    예를들어: "person"이라고 치면 사람만 남고 나머지 배경은 삭제 됩니다.
    """)

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
                                               "segmentation_api.py")
                result = subprocess.run(
                    ['python', api_script_path, temp_path, segment_text],
                    capture_output=True, text=True
                )

                # Display any errors
                if result.stderr:
                    st.error(f'Error occurred during processing: {result.stderr}')

                # Show the command output for debugging
                if st.checkbox('디버깅'):
                    st.code(result.stdout)

                # Read and display results
                output_dir = os.path.join("E:", "ComfyUI_windows_portable", "comfyui_websockets", "output_files")
                output_list_path = os.path.join(output_dir, "output_files.txt")

                if os.path.exists(output_list_path):
                    with open(output_list_path, 'r') as f:
                        output_files = f.read().splitlines()

                    # Display segmented images
                    st.write("Segmentation Result:")
                    for file in output_files:
                        if file.endswith('.png'):
                            st.image(file)
                            # Clean up the output file
                            try:
                                os.remove(file)
                            except Exception as e:
                                st.error(f"Error removing file {file}: {str(e)}")

                    # Clean up the output files list
                    try:
                        os.remove(output_list_path)
                    except Exception as e:
                        st.error(f"Error removing output list: {str(e)}")

                    # Show success message at the bottom
                    st.markdown("---")
                    st.success("Segmentation이 완료되었습니다.")

                else:
                    st.error("No output files were generated. Please check the processing details.")

                # Clean up the temporary upload file
                try:
                    os.remove(temp_path)
                except Exception as e:
                    st.error(f"Error removing temp file: {str(e)}")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    st.markdown("---")
    st.markdown("""
    ### Tips for best results:
    1. 깨끗하고 고화질일수록 잘 됩니다.
    2. 객체가 잘 보이는 사진을 업로드 해주세요.
    3. 정확한 설명의 프롬프트를 입력해주세요.
    """)