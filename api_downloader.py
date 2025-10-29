from flask import Flask, request, jsonify, send_file
from pytubefix import YouTube
import os
import uuid
import traceback

app = Flask(__name__)

# Render는 실행 시 임시 저장소가 필요할 수 있습니다.
TEMP_DIR = "temp_downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route('/')
def home():
    # 서버가 살아있는지 확인하기 위한 핑(Ping) 엔드포인트
    return "Downloader API is alive!"

@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    temp_path = None
    try:
        print(f"Received request for URL: {url}")
        yt = YouTube(url)
        
        # FFmpeg 없는 환경이므로 progressive (결합된) 스트림 검색
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            print("No progressive MP4 found, trying any progressive.")
            stream = yt.streams.filter(progressive=True).order_by('resolution').desc().first()
        
        if not stream:
            print("No progressive streams found.")
            return jsonify({"error": "No progressive stream found"}), 404

        # 고유한 파일명으로 임시 저장
        filename = f"{uuid.uuid4()}.mp4"
        temp_path = os.path.join(TEMP_DIR, filename)
        
        print(f"Downloading stream to: {temp_path}")
        stream.download(output_path=TEMP_DIR, filename=filename)
        print("Download complete.")

        # ⭐️ 클라이언트(HF 서버)에게 파일 전송
        #    as_attachment=True는 이 응답이 '파일'임을 알립니다.
        return send_file(temp_path, as_attachment=True, download_name="video.mp4")

    except Exception as e:
        print(f"Error processing {url}: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        # ⭐️ 파일 전송이 끝난 후, 임시 파일 삭제
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"Cleaned up: {temp_path}")
            except Exception as e:
                print(f"Error cleaning up file {temp_path}: {e}")

if __name__ == '__main__':
    # Render는 Gunicorn을 사용하지만, 로컬 테스트를 위해 남겨둠
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
