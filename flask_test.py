from flask import Flask, request, jsonify
import base64
from PIL import Image
from io import BytesIO
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'fail', 'message': 'No JSON data received'}), 400

        rgb_image_data = data.get('rgb_image')
        mask_image_data = data.get('mask_image')

        if not rgb_image_data or not mask_image_data:
            return jsonify({'status': 'fail', 'message': 'Missing image data'}), 400

        # Base64 디코딩 및 이미지 로드
        rgb_image = decode_image(rgb_image_data)
        mask_image = decode_image(mask_image_data)

        # 디렉토리 생성
        save_directory = './received_images'
        os.makedirs(save_directory, exist_ok=True)

        # 이미지 저장
        rgb_image_path = os.path.join(save_directory, 'rgb_image.png')
        mask_image_path = os.path.join(save_directory, 'mask_image.png')
        rgb_image.save(rgb_image_path)
        mask_image.save(mask_image_path)

        # 추가적인 이미지 처리 로직을 여기에 추가할 수 있습니다.
        # ...

        return jsonify({'status': 'success', 'message': 'Images received and saved'}), 200

    except Exception as e:
        print(f"Error processing images: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def decode_image(base64_string):
    """
    Base64로 인코딩된 이미지를 디코딩하여 PIL 이미지로 반환하는 함수.
    """
    image_data = base64.b64decode(base64_string)
    image = Image.open(BytesIO(image_data))
    return image

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)