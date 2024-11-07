import requests
import random
import json
import base64
import os
import sys
from PIL import Image
import io
import time
import shutil


def upload_image(image_path):
    """
    ComfyUI 서버에 이미지를 업로드하는 함수
    Args:
        image_path: 업로드할 이미지의 경로
    Returns:
        업로드된 이미지의 파일명
    """
    try:
        print(f"Uploading image from: {image_path}")

        # multipart/form-data 형식으로 파일 업로드 준비
        files = {
            'image': ('image.png', open(image_path, 'rb'), 'image/png')
        }

        # ComfyUI의 업로드 엔드포인트로 POST 요청
        response = requests.post(
            'http://127.0.0.1:8188/upload/image',
            files=files
        )

        print(f"Upload response status: {response.status_code}")
        print(f"Upload response content: {response.content}")

        # 업로드 실패 시 예외 발생
        if response.status_code != 200:
            raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

        # 응답에서 업로드된 파일명 추출
        result = response.json()
        if 'name' not in result:
            raise Exception(f"Upload response missing filename: {result}")

        return result['name']

    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        raise
    finally:
        # 파일 핸들러 정리
        files['image'][1].close()


def queue_prompt(prompt):
    """
    ComfyUI 서버에 작업을 큐에 추가하는 함수
    Args:
        prompt: 실행할 워크플로우 정보
    Returns:
        서버 응답 (prompt_id 포함)
    """
    try:
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        # 워크플로우 실행 요청
        response = requests.post(
            'http://127.0.0.1:8188/prompt',
            json=prompt,
            headers=headers
        )

        print("Response status:", response.status_code)
        print("Raw response:", response.text)

        if response.status_code != 200:
            raise requests.exceptions.HTTPError(
                f"HTTP {response.status_code}: {response.text}"
            )

        return response.json()
    except Exception as e:
        print(f"Error in queue_prompt: {str(e)}")
        raise


def get_image(filename, subfolder, folder_type):
    """
    ComfyUI 서버에서 생성된 이미지를 가져오는 함수
    Args:
        filename: 이미지 파일명
        subfolder: 하위 폴더명
        folder_type: 폴더 유형
    Returns:
        이미지 데이터 (바이너리)
    """
    try:
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        response = requests.get(f'http://127.0.0.1:8188/view', params=data)
        return response.content
    except Exception as e:
        print(f"Error in get_image: {str(e)}")
        raise


def get_history(prompt_id):
    """
    ComfyUI 서버에서 작업 실행 기록을 가져오는 함수
    Args:
        prompt_id: 작업 ID
    Returns:
        작업 실행 기록 정보
    """
    try:
        response = requests.get(f'http://127.0.0.1:8188/history/{prompt_id}')
        return response.json()
    except Exception as e:
        print(f"Error in get_history: {str(e)}")
        raise


def run_segmentation(input_image_path, segment_text):
    """
    이미지 세그멘테이션을 실행하는 메인 함수
    Args:
        input_image_path: 입력 이미지 경로
        segment_text: 세그멘테이션할 객체 설명
    Returns:
        생성된 이미지 파일들의 경로 리스트
    """
    try:
        # 이미지 업로드
        print(f"Uploading image: {input_image_path}")
        uploaded_filename = upload_image(input_image_path)
        print(f"Image uploaded as: {uploaded_filename}")

        # 랜덤 시드 생성
        seed = random.randint(1, 99999999)
        print(f"Using seed: {seed}")

        # 워크플로우 정의
        # 각 노드는 ComfyUI의 워크플로우 구성요소를 나타냄
        workflow = {
            "4": {  # SAM2 모델 로드 노드
                "inputs": {
                    "model": "sam2_hiera_base_plus.safetensors",
                    "segmentor": "single_image",
                    "device": "cuda",
                    "precision": "fp16"
                },
                "class_type": "DownloadAndLoadSAM2Model"
            },
            "6": {  # Florence2 모델 로드 노드
                "inputs": {
                    "model": "microsoft/Florence-2-base",
                    "precision": "fp16",
                    "attention": "sdpa"
                },
                "class_type": "DownloadAndLoadFlorence2Model"
            },
            "11": {  # 이미지 로드 노드
                "inputs": {
                    "image": uploaded_filename,
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "5": {  # Florence2 실행 노드 (텍스트 기반 객체 위치 찾기)
                "inputs": {
                    "text_input": segment_text,
                    "task": "caption_to_phrase_grounding",
                    "fill_mask": True,
                    "keep_model_loaded": False,
                    "max_new_tokens": 1024,
                    "num_beams": 3,
                    "do_sample": True,
                    "output_mask_select": "",
                    "seed": seed,
                    "image": ["11", 0],
                    "florence2_model": ["6", 0]
                },
                "class_type": "Florence2Run"
            },
            "7": {  # Florence2 좌표 변환 노드
                "inputs": {
                    "data": ["5", 3],
                    "index": "0",
                    "batch": False
                },
                "class_type": "Florence2toCoordinates"
            },
            "3": {  # SAM2 세그멘테이션 노드
                "inputs": {
                    "sam2_model": ["4", 0],
                    "image": ["11", 0],
                    "coordinates_positive": ["7", 0],
                    "keep_model_loaded": True,
                    "individual_objects": False
                },
                "class_type": "Sam2Segmentation"
            },
            "2": {  # 마스크 반전 노드
                "inputs": {
                    "mask": ["3", 0]
                },
                "class_type": "InvertMask"
            },
            "1": {  # 이미지와 알파 채널 결합 노드
                "inputs": {
                    "image": ["11", 0],
                    "alpha": ["2", 0]
                },
                "class_type": "JoinImageWithAlpha"
            },
            "12": {  # 이미지 저장 노드
                "inputs": {
                    "images": ["1", 0],
                    "filename_prefix": "segment_output"
                },
                "class_type": "SaveImage"
            }
        }

        # 프롬프트 생성
        prompt = {
            "prompt": workflow,
            "client_id": f"segmentation_{random.randint(1, 1000000)}"
        }

        # 작업 큐에 추가
        print("Queueing prompt...")
        print(f"LoadImage configuration: {json.dumps(workflow['11'], indent=2)}")

        response = queue_prompt(prompt)
        print("Queue response:", response)

        prompt_id = response["prompt_id"]
        print(f"Prompt ID: {prompt_id}")

        # 처리 완료 대기
        print("Waiting for processing...")
        max_attempts = 30
        attempts = 0

        while attempts < max_attempts:
            history = get_history(prompt_id)
            if prompt_id in history and len(history[prompt_id]["outputs"]) > 0:
                break
            attempts += 1
            time.sleep(1)
            print(f"Waiting... Attempt {attempts}/{max_attempts}")

        if attempts >= max_attempts:
            raise Exception("Timeout waiting for processing")

        # 생성된 이미지 가져오기
        output_images = []
        history = history[prompt_id]

        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "images" in node_output:
                for image in node_output["images"]:
                    image_data = get_image(image["filename"], image["subfolder"], image["type"])
                    output_images.append(image_data)

        if not output_images:
            raise Exception("No output images generated")

        # 결과 이미지 저장
        saved_files = []
        output_dir = os.path.join("E:", "ComfyUI_windows_portable", "comfyui_websockets", "output_files")
        os.makedirs(output_dir, exist_ok=True)

        for i, image_data in enumerate(output_images):
            output_path = os.path.join(output_dir, f"segmented_{i}.png")
            with open(output_path, 'wb') as f:
                f.write(image_data)
            saved_files.append(output_path)

        # 출력 파일 목록 저장
        output_list_path = os.path.join(output_dir, "output_files.txt")
        with open(output_list_path, 'w') as f:
            for file in saved_files:
                f.write(f"{file}\n")

        print(f"Saved {len(saved_files)} files")
        return saved_files

    except Exception as e:
        print(f"Error in run_segmentation: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        raise


if __name__ == "__main__":
    # 명령줄 인자 검사
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_image_path> <segment_text>")
        sys.exit(1)

    # 입력 파라미터 가져오기
    input_image_path = sys.argv[1]
    segment_text = sys.argv[2]

    # 세그멘테이션 실행
    output_files = run_segmentation(input_image_path, segment_text)
    print("Output files:", output_files)