from flask import Flask, request, jsonify, send_file
import yt_dlp  # ⭐️ Pytubefix에서 변경
import os
import uuid
import traceback

app = Flask(__name__)

TEMP_DIR = "temp_downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route('/')
def home():
    # ⭐️ 버전2임을 표시 (yt-dlp 사용)
    return "Downloader API is alive! (v2: yt-dlp)"

@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    temp_path = None
    try:
        print(f"Received request for URL: {url} (using yt-dlp)")

        # 1. 고유한 파일명 템플릿 생성
        unique_id = str(uuid.uuid4())
        output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")
        
        # 2. yt-dlp 옵션 설정 (FFmpeg 없이 합쳐진 mp4 요청)
        ydl_opts = {
            'format': 'best[ext=mp4]/best', 
            'outtmpl': output_template,
            'quiet': True,
            'noplaylist': True,
        }

        print("Starting download with yt-dlp...")
        
        # 3. yt-dlp로 다운로드
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 먼저 정보를 가져와서 확장자(ext)를 알아냅니다.
            info = ydl.extract_info(url, download=False)
            ext = info.get('ext', 'mp4')
            
            # 최종 파일 경로 확정
            temp_path = os.path.join(TEMP_DIR, f"{unique_id}.{ext}")
            
            # 실제 다운로드 실행
            ydl.download([url])

        print(f"Download complete: {temp_path}")

        # 다운로드된 파일이 있는지 확인
        if not os.path.exists(temp_path):
             # 확장자가 달랐을 경우를 대비해 다시 찾기
            for f in os.listdir(TEMP_DIR):
                if f.startswith(unique_id):
                    temp_path = os.path.join(TEMP_DIR, f)
                    break
            if not os.path.exists(temp_path):
                raise Exception("yt-dlp downloaded, but file not found.")

        # 4. Hugging Face 앱(클라이언트)에게 파일 전송
        return send_file(temp_path, as_attachment=True, download_name=f"video.{ext}")

    except Exception as e:
        error_message = f"Error processing {url} with yt-dlp: {e}"
        print(error_message)
        traceback.print_exc()
        return jsonify({"error": error_message}), 500
    finally:
        # 5. 임시 파일 삭제
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"Cleaned up: {temp_path}")
            except Exception as e:
                print(f"Error cleaning up file {temp_path}: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
