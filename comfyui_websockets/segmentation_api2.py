import requests
import random
import json
import base64
import os
import sys
from PIL import Image
import io
import time
import glob


def queue_prompt(prompt):
    """ComfyUI 서버에 프롬프트를 전송하고 응답을 받는 함수"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
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


def upload_image(image_path):
    """이미지를 ComfyUI 서버에 업로드하는 함수"""
    try:
        print(f"Uploading image from: {image_path}")

        files = {
            'image': ('image.png', open(image_path, 'rb'), 'image/png')
        }

        response = requests.post(
            'http://127.0.0.1:8188/upload/image',
            files=files
        )

        print(f"Upload response status: {response.status_code}")
        print(f"Upload response content: {response.content}")

        if response.status_code != 200:
            raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

        result = response.json()
        if 'name' not in result:
            raise Exception(f"Upload response missing filename: {result}")

        return result['name']

    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        raise
    finally:
        files['image'][1].close()


def get_history(prompt_id):
    """ComfyUI 서버에서 프롬프트 실행 기록을 가져오는 함수"""
    try:
        response = requests.get(f'http://127.0.0.1:8188/history/{prompt_id}')
        return response.json()
    except Exception as e:
        print(f"Error in get_history: {str(e)}")
        raise


def get_latest_image(directory):
    """지정된 디렉토리에서 가장 최근에 생성된 이미지 파일 찾기"""
    files = glob.glob(os.path.join(directory, "temp_seg_*.png"))
    if not files:
        return None
    return max(files, key=os.path.getctime)


def image_to_base64(image_path):
    """이미지 파일을 Base64로 변환"""
    try:
        # 경로가 리스트인 경우 첫 번째 항목 사용
        if isinstance(image_path, list):
            image_path = image_path[0]

        # 경로에서 불필요한 이스케이프 문자 제거 및 정규화
        image_path = os.path.normpath(image_path.replace('\\\\', '\\'))

        # 파일이 존재하지 않으면 디렉토리에서 최신 파일 찾기
        if not os.path.exists(image_path):
            directory = os.path.dirname(image_path)
            latest_image = get_latest_image(directory)
            if latest_image:
                image_path = latest_image
            else:
                raise FileNotFoundError(f"No image files found in {directory}")

        print(f"Reading image from: {image_path}")

        with Image.open(image_path) as img:
            # RGBA를 RGB로 변환
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return None


def run_segmentation(input_image_path, segment_text):
    """이미지 세그멘테이션을 실행하고 결과를 반환하는 메인 함수"""
    try:
        print(f"Uploading image: {input_image_path}")
        uploaded_filename = upload_image(input_image_path)
        print(f"Image uploaded as: {uploaded_filename}")

        seed = random.randint(1, 99999999)
        print(f"Using seed: {seed}")

        # ComfyUI에 전달할 절대 경로 설정
        base_path = "E:/ComfyUI_windows_portable/comfyui_websockets"  # 슬래시 사용
        save_path = os.path.join(base_path, "temp_seg")

        # temp_seg 디렉토리 초기화
        if os.path.exists(save_path):
            for f in glob.glob(os.path.join(save_path, "temp_seg_*.png")):
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Error removing old file {f}: {e}")
        os.makedirs(save_path, exist_ok=True)

        print(f"Saving results to: {save_path}")

        workflow = {
            "4": {
                "inputs": {
                    "model": "sam2_hiera_base_plus.safetensors",
                    "segmentor": "single_image",
                    "device": "cuda",
                    "precision": "fp16"
                },
                "class_type": "DownloadAndLoadSAM2Model"
            },
            "6": {
                "inputs": {
                    "model": "microsoft/Florence-2-base",
                    "precision": "fp16",
                    "attention": "sdpa"
                },
                "class_type": "DownloadAndLoadFlorence2Model"
            },
            "11": {
                "inputs": {
                    "image": uploaded_filename,
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "5": {
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
            "7": {
                "inputs": {
                    "data": ["5", 3],
                    "index": "0",
                    "batch": False
                },
                "class_type": "Florence2toCoordinates"
            },
            "3": {
                "inputs": {
                    "sam2_model": ["4", 0],
                    "image": ["11", 0],
                    "coordinates_positive": ["7", 0],
                    "keep_model_loaded": True,
                    "individual_objects": False
                },
                "class_type": "Sam2Segmentation"
            },
            "2": {
                "inputs": {
                    "mask": ["3", 0]
                },
                "class_type": "InvertMask"
            },
            "1": {
                "inputs": {
                    "image": ["11", 0],
                    "alpha": ["2", 0]
                },
                "class_type": "JoinImageWithAlpha"
            },
            "13": {
                "inputs": {
                    "prefix_name": "temp_seg_",
                    "save_path": save_path.replace('\\', '/'),  # 슬래시 사용
                    "image_format": "png",
                    "use_api": False,
                    "image": ["1", 0]
                },
                "class_type": "restsaveandsend"
            },
            "14": {
                "inputs": {
                    "text": ["13", 0]
                },
                "class_type": "ShowText|pysssss"
            }
        }

        prompt = {
            "prompt": workflow,
            "client_id": f"segmentation_{random.randint(1, 1000000)}"
        }

        print("Queueing prompt...")
        response = queue_prompt(prompt)
        prompt_id = response["prompt_id"]
        print(f"Prompt ID: {prompt_id}")

        max_attempts = 30
        attempts = 0

        while attempts < max_attempts:
            history = get_history(prompt_id)
            if prompt_id in history and "14" in history[prompt_id].get("outputs", {}):
                saved_path = history[prompt_id]["outputs"]["14"]["text"]
                print(f"Image saved to: {saved_path}")

                # 최신 이미지 찾기
                latest_image = get_latest_image(save_path)
                if latest_image:
                    print(f"Found latest image: {latest_image}")
                    base64_result = image_to_base64(latest_image)

                    if base64_result:
                        # 임시 파일 삭제
                        try:
                            os.remove(latest_image)
                            print(f"Temporary file removed: {latest_image}")
                        except Exception as e:
                            print(f"Error removing temporary file: {e}")

                        return base64_result

            attempts += 1
            time.sleep(1)
            print(f"Waiting... Attempt {attempts}/{max_attempts}")

        if attempts >= max_attempts:
            raise Exception("Timeout waiting for processing")

    except Exception as e:
        print(f"Error in run_segmentation: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python segmentation_api2.py <input_image_path> <segment_text>")
        sys.exit(1)

    input_image_path = sys.argv[1]
    segment_text = sys.argv[2]
    output_info = run_segmentation(input_image_path, segment_text)
    print(output_info)  # Base64 출력