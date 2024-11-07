import random
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import sys
import time
import os

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    output_videos = {}
    output_translated = {}
    output_LLM = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break
        else:
            continue

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            #print("node output",node_output)

            if node_id =='24':
                output_translated=node_output['text'][0]
            if node_id =='25':
                output_LLM=node_output['text'][0]

            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
                output_images[node_id] = images_output
            if 'gifs' in node_output:
                videos_output = []
                for video in node_output['gifs']:
                    video_data = get_image(video['filename'], video['subfolder'], video['type'])
                    videos_output.append(video_data)
                output_videos[node_id] = videos_output

    return output_images, output_videos, output_translated, output_LLM

# main function
if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python kor2vid.py <kor_text> <ckpt_name> <width> <height> <frames>")
        sys.exit(1)

    with open("E:/ComfyUI_windows_portable/comfyui_websockets/0808_kor2vid.json", "r", encoding="utf-8") as f:
        workflow_data = f.read()

    workflow = json.loads(workflow_data)

    # seed
    seed = random.randint(1, 99999999)
    workflow["38"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["seed"] = seed
    workflow["17"]["inputs"]["seed"] = seed
    workflow["21"]["inputs"]["seed"] = seed

    # kor input
    kor = sys.argv[1]
    workflow["23"]["inputs"]["input_field"] = kor

    # checkpoint
    ckpt_name = sys.argv[2]
    workflow["4"]["inputs"]["ckpt_name"] = ckpt_name

    # size
    width = int(sys.argv[3])
    height = int(sys.argv[4])
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height

    # Resize image
    workflow["11"]["inputs"]["width"] = width
    workflow["11"]["inputs"]["height"] = height

    #frames
    workflow["17"]["inputs"]["frames"]=int(sys.argv[5])*8

    print("seed:", seed)
    print("kor:", kor)
    print("ckpt_name:", ckpt_name)
    print("width x height:", width,'x',height)

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images, videos, translate, LLM = get_images(ws, workflow)

    print("translate:", translate)
    print("prompt:", LLM)

    # Saving images and videos to disk for Streamlit
    output_dir = "output_files"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    output_files = []

    for node_id in images:
        for i, image_data in enumerate(images[node_id]):
            image_filename = os.path.join(output_dir, f"output_image_{node_id}_{i}_{timestamp}.png")
            with open(image_filename, "wb") as img_file:
                img_file.write(image_data)
            output_files.append(image_filename)
            # print(f"Saved image: {image_filename}")

    for node_id in videos:
        for i, video_data in enumerate(videos[node_id]):
            video_filename = os.path.join(output_dir, f"output_video_{node_id}_{i}_{timestamp}.mp4")
            with open(video_filename, "wb") as video_file:
                video_file.write(video_data)
            output_files.append(video_filename)
            # print(f"Saved video: {video_filename}")

    with open(os.path.join(output_dir, "output_files.txt"), "w") as f:
        for file in output_files:
            f.write(file + "\n")