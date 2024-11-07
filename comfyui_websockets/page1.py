import streamlit as st
import subprocess
import os
import json

def run():
    # Streamlit 타이틀
    st.title('Kor2Video')

    # 사용자로부터 텍스트 입력 받기
    user_input = st.text_input('만들고싶은 비디오:')

    # 이미지 가로 및 세로 크기 입력 받기
    image_width = st.number_input('이미지 가로 크기(px):', min_value=1, value=1024)
    image_height = st.number_input('이미지 세로 크기(px):', min_value=1, value=576)

    # 체크포인트 목록
    checkpoints = [
        "animagineXLV31_v31.safetensors",
        "baxlBlueArchiveFlatCelluloidStyleFineTune_xlv3.safetensors",
        "copaxTimelessxlSDXL1_v12.safetensors",
        "dreamshaperXL_v21TurboDPMSDE.safetensors",
        "modernDisneyXL_v3.safetensors",
        "henmix25D_v20.safetensors",
        "henmixReal_v5c.safetensors"
    ]

    # 체크포인트 설명 사전 (기본 설명)
    checkpoint_descriptions = {
        "animagineXLV31_v31.safetensors": "범용적인 2D애니 이미지를 만들어냅니다.",
        "baxlBlueArchiveFlatCelluloidStyleFineTune_xlv3.safetensors": "일본스러운 2D애니 이미지를 만들어 냅니다.",
        "copaxTimelessxlSDXL1_v12.safetensors": "실사 이미지를 만들때 유리합니다",
        "dreamshaperXL_v21TurboDPMSDE.safetensors": "실사+우주기반 이미지를 만들때 유리합니다.",
        "modernDisneyXL_v3.safetensors": "3D 디즈니풍을 만들때 유리합니다.",
        "henmix25D_v20.safetensors": "2.5D 이미지를 만들어냅니다. 인물의 외형이 한국인이며 예쁘고 잘생긴 인물을 만들때 유리합니다.",
        "henmixReal_v5c.safetensors": "실사 이미지를 만들어냅니다. 인물의 외형이 한국인이며 예쁘고 잘생긴 인물을 만들때 유리합니다."
    }

    # 사용자로부터 체크포인트 선택 받기
    ckpt_selection = st.selectbox('체크포인트를 선택하세요:', checkpoints)

    # 선택된 체크포인트 설명 표시 및 수정 가능
    checkpoint_description = st.text_area('선택된 체크포인트 설명:', checkpoint_descriptions[ckpt_selection])

    #초수 입력
    playtime=['1','2','3','4']
    playtime_selection = st.selectbox('동영상 길이를 선택하세요(초):', playtime)

    # 텍스트가 입력되었을 때 실행
    if st.button('실행'):
        if user_input and ckpt_selection:
            # Python 스크립트 실행
            result = subprocess.run(
                ['python', 'E:/ComfyUI_windows_portable/comfyui_websockets/kor2vid.py', user_input, ckpt_selection, str(image_width), str(image_height), playtime_selection],
                capture_output=True, text=True
            )
            # result = subprocess.run(
            #     ['python', 'E:/ComfyUI_windows_portable/comfyui_websockets/rest_api_old.py', user_input, ckpt_selection, str(image_width), str(image_height), playtime_selection],
            #     capture_output=True, text=True
            # )

            # 스크립트 실행 결과 출력
            st.write('스크립트 출력:')
            st.text(result.stdout)

            # 스크립트 에러 출력
            st.write('스크립트 에러:')
            st.text(result.stderr)

            # 결과 파일 목록 읽기
            output_dir = "output_files"
            if os.path.exists(os.path.join(output_dir, "output_files.txt")):
                with open(os.path.join(output_dir, "output_files.txt"), 'r') as f:
                    output_files = f.read().splitlines()

                # 결과 이미지 표시
                st.write('결과 이미지 & 얼굴보정 이미지')
                for file in output_files:
                    if file.endswith('.png'):
                        st.image(file)
                        os.remove(file)

                # 결과 동영상 표시
                st.write('결과 동영상')
                for file in output_files:
                    if file.endswith('.mp4'):
                        st.text(result.stderr)
                        st.video(file)
                        os.remove(file)

                # 파일 목록 삭제
                os.remove(os.path.join(output_dir, "output_files.txt"))
        else:
            st.write('텍스트를 입력하세요.')
