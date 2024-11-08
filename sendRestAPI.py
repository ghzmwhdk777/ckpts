import os
import requests
import torch
import numpy as np
from PIL import Image
import base64
import json


class SendImageAndMask:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "rgb_image": ("IMAGE",),
                "mask_image": ("MASK",),
                "api_endpoint": ("STRING", {
                    "default": "http://localhost:8501/stream",
                    "lazy": False
                })
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("rgb_image", "mask_image", "rgb_base64")
    FUNCTION = "send_images"
    CATEGORY = "ImageSender"

    def send_images(self, rgb_image, mask_image, api_endpoint):
        """
        RGB 이미지와 마스크 이미지를 REST API를 통해 JSON으로 전송하는 함수.
        """
        # 1. 이미지 텐서를 PIL 이미지로 변환
        rgb_pil = self.tensor_to_pil(rgb_image, is_mask=False)
        mask_pil = self.tensor_to_pil(mask_image, is_mask=True)

        # 2. 이미지를 Base64로 인코딩
        rgb_base64 = self.pil_to_base64(rgb_pil)
        mask_base64 = self.pil_to_base64(mask_pil)

        # 3. JSON 데이터 생성
        data = {
            "rgb_image": rgb_base64,
            "mask_image": mask_base64
        }

        # 4. REST API로 전송
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(api_endpoint, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                print(f"Successfully sent images to {api_endpoint}")
            else:
                print(f"Failed to send images to {api_endpoint}. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error while sending images to API: {e}")

        # 5. 입력받은 이미지를 그대로 반환하여 출력값 제공
        return (rgb_image, mask_image, rgb_base64)

    def tensor_to_pil(self, image_tensor, is_mask=False):
        """
        텐서를 PIL 이미지로 변환하는 함수
        is_mask: True인 경우 마스크 이미지로 처리
        """
        # 텐서를 NumPy 배열로 변환
        if torch.is_tensor(image_tensor):
            image = image_tensor.cpu().numpy()
        else:
            image = image_tensor

        # 이미지 차원 조정
        if len(image.shape) == 4:  # (B, C, H, W)
            image = image[0]  # 첫 번째 배치 선택

        if is_mask:
            # 마스크 이미지 처리
            if len(image.shape) == 3 and image.shape[0] == 1:  # (1, H, W)
                image = image[0]  # 첫 번째 채널 선택
            # 값 범위를 0-255로 조정
            image = (image * 255).astype(np.uint8)
            # 그레이스케일 이미지로 변환
            return Image.fromarray(image, mode='L')
        else:
            # RGB 이미지 처리
            if image.shape[0] in [1, 3, 4]:  # (C, H, W)
                image = np.transpose(image, (1, 2, 0))  # (H, W, C)

            # 값 범위 조정
            if np.max(image) <= 1.0:
                image = image * 255
            image = np.clip(image, 0, 255).astype(np.uint8)

            # RGB 이미지로 변환
            if image.shape[-1] == 1:  # 단일 채널
                image = np.repeat(image, 3, axis=-1)
            return Image.fromarray(image)

    def pil_to_base64(self, pil_image):
        # PIL 이미지를 Base64 문자열로 변환
        from io import BytesIO
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str


NODE_CLASS_MAPPINGS = {
    "SendImageAndMask": SendImageAndMask
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SendImageAndMask": "Send Image and Mask via REST API"
}