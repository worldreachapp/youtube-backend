from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)  # Allow requests from your Cloudflare Worker

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'message': 'YouTube Download API',
        'version': '1.0'
    })

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        quality = data.get('quality', '720')
        
        if not video_id:
            return jsonify({
                'success': False,
                'message': 'videoId is required'
            }), 400
        
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        # Get list of all available formats first
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'quiet': False,
            'no_warnings': False,
            'merge_output_format': 'mp4'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Try to get URL from different possible fields
            download_url = None
            
            # Check if there's a direct URL
            if 'url' in info and info['url']:
                download_url = info['url']
            # Check requested_formats (for merged video+audio)
            elif 'requested_formats' in info and info['requested_formats']:
                # Return the video URL from first format
                download_url = info['requested_formats'][0].get('url')
            # Check formats array
            elif 'formats' in info and info['formats']:
                # Find best format with url
                for fmt in reversed(info['formats']):
                    if fmt.get('url'):
                        download_url = fmt['url']
                        break
            
            if not download_url:
                return jsonify({
                    'success': False,
                    'message': 'Could not extract download URL'
                }), 500
            
            return jsonify({
                'success': True,
                'url': download_url,
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'quality': 'Best available with audio',
                'filesize': info.get('filesize', 0)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/info', methods=['POST'])
def video_info():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        
        if not video_id:
            return jsonify({
                'success': False,
                'message': 'videoId is required'
            }), 400
        
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get available formats
            formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('ext') in ['mp4', 'webm']:
                    formats.append({
                        'quality': f.get('format_note', 'unknown'),
                        'ext': f.get('ext'),
                        'filesize': f.get('filesize', 0)
                    })
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'formats': formats[:10]  # Return first 10 formats
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
