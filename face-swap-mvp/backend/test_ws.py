import asyncio
import cv2
import websockets
import os

async def test_ws():
    # 1. upload a source face
    import requests
    source_img_path = "scripts/test_images/source.png"
    with open(source_img_path, "rb") as f:
        res = requests.post("http://localhost:8000/api/upload-face", files={"file": f})
    print("Upload result:", res.json())

    # 2. connect to ws
    uri = "ws://localhost:8000/api/ws/swap?enhance=false"
    async with websockets.connect(uri) as websocket:
        print("Connected.")
        
        # 3. read a target image and send as jpeg
        img = cv2.imread("scripts/test_images/target.png")
        _, buf = cv2.imencode(".jpg", img)
        await websocket.send(buf.tobytes())
        print("Sent frame.")
        
        # 4. receive result
        data = await websocket.recv()
        print(f"Received data of length {len(data)}")

asyncio.run(test_ws())
