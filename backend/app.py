# app.py - Backend Flask per Timestamp Clip Extractor
import os
import json
import threading
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import re
import hashlib
import zipfile
import tempfile
import shutil

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Global storage per task progress (in produzione usare Redis)
task_progress = {}
task_results = {}

# Directory per file temporanei
TEMP_DIR = "temp_clips"
os.makedirs(TEMP_DIR, exist_ok=True)

class TimestampClipExtractor:
    """Classe principale per estrazione clip"""
    
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self.setup_extractor()
    
    def setup_extractor(self):
        """Setup iniziale"""
        print("🔧 Setup Timestamp Clip Extractor...")
        
        # Verifica yt-dlp
        result = subprocess.run("yt-dlp --version", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print("📦 Installando yt-dlp...")
            subprocess.run("pip install yt-dlp --upgrade --quiet", shell=True)
        
        print("✅ Setup completato!")
    
    def parse_timestamp(self, timestamp_str):
        """Converte timestamp in secondi"""
        timestamp_str = timestamp_str.strip()
        
        if timestamp_str.isdigit():
            return int(timestamp_str)
        
        parts = timestamp_str.split(':')
        
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError(f"Formato timestamp non valido: {timestamp_str}")
    
    def parse_timestamps_input(self, timestamps_text):
        """Estrae timestamp da testo formattato"""
        print("📋 Parsing timestamp...")
        
        pattern = r'(\d+:\d+:\d+)\s+Stream Time Marker\s*-?\s*(.*)'
        
        matches = re.findall(pattern, timestamps_text, re.MULTILINE)
        
        if not matches:
            print("⚠️ Nessun timestamp 'Stream Time Marker' trovato")
            return []
        
        timestamps = []
        for match in matches:
            try:
                seconds = self.parse_timestamp(match[0])
                timestamps.append({
                    'original': match[0],
                    'seconds': seconds,
                    'description': match[1].strip() if match[1].strip() else f"Evento al {match[0]}"
                })
            except ValueError as e:
                print(f"⚠️ Errore timestamp {match[0]}: {e}")
        
        print(f"✅ Trovati {len(timestamps)} timestamp validi")
        return timestamps
    
    def download_clip_from_timestamp(self, video_url, timestamp_seconds, clip_duration=60, url_hash="", clip_index=0):
        """Scarica clip da timestamp specifico"""
        
        start_time = max(0, timestamp_seconds - clip_duration)
        
        timestamp_min = timestamp_seconds // 60
        timestamp_sec = timestamp_seconds % 60
        
        output_file = os.path.join(
            self.temp_dir, 
            f"timestamp_clip_{url_hash}_{clip_index+1}_{timestamp_min:02d}m{timestamp_sec:02d}s.mp4"
        )
        
        print(f"⬇️ Clip {clip_index+1}: {timestamp_min:02d}:{timestamp_sec:02d}")
        
        # Comando download
        cmd = [
            'yt-dlp',
            '-f', 'best[height<=720]',
            '--external-downloader', 'ffmpeg',
            '--external-downloader-args', f'ffmpeg:-ss {start_time} -t {clip_duration}',
            '-o', output_file,
            video_url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0 and os.path.exists(output_file):
                file_size = os.path.getsize(output_file) / (1024*1024)
                print(f"  ✅ Clip {clip_index+1} creata: {output_file} ({file_size:.1f} MB)")
                
                return {
                    'success': True,
                    'file': output_file,
                    'filename': os.path.basename(output_file),
                    'timestamp': timestamp_seconds,
                    'start_time': start_time,
                    'duration': clip_duration,
                    'size_mb': file_size
                }
            else:
                print(f"  ❌ Errore clip {clip_index+1}")
                print(f"  Error: {result.stderr}")
                return {
                    'success': False,
                    'timestamp': timestamp_seconds,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            print(f"  ⏰ Timeout clip {clip_index+1}")
            return {
                'success': False,
                'timestamp': timestamp_seconds,
                'error': 'Timeout'
            }
    
    def create_zip_package(self, clips, task_id):
        """Crea ZIP con tutte le clip riuscite"""
        
        zip_filename = f"timestamp_clips_{task_id}.zip"
        zip_path = os.path.join(self.temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            files_added = 0
            
            for clip in clips:
                if clip.get('success') and os.path.exists(clip['file']):
                    zipf.write(clip['file'], clip['filename'])
                    files_added += 1
            
            # Aggiungi report JSON
            report_data = {
                'extraction_date': datetime.now().isoformat(),
                'total_clips': len(clips),
                'successful_clips': files_added,
                'clips': clips
            }
            
            report_json = json.dumps(report_data, indent=2)
            zipf.writestr('extraction_report.json', report_json)
        
        if files_added > 0:
            return zip_path, files_added
        else:
            os.remove(zip_path)
            return None, 0
    
    def extract_clips(self, video_url, timestamps_input, clip_duration, task_id, progress_callback=None):
        """Funzione principale per estrazione clip"""
        
        try:
            # Parse timestamps
            if progress_callback:
                progress_callback(10, "Parsing timestamp...")
            
            timestamps_data = self.parse_timestamps_input(timestamps_input)
            
            if not timestamps_data:
                return {
                    'success': False,
                    'error': 'Nessun timestamp valido trovato'
                }
            
            # Hash per nomi file
            url_hash = hashlib.md5(video_url.encode()).hexdigest()[:6]
            
            # Download clips
            clips = []
            total_clips = len(timestamps_data)
            
            for i, timestamp_data in enumerate(timestamps_data):
                if progress_callback:
                    progress = 20 + (i / total_clips) * 60  # 20-80%
                    progress_callback(int(progress), f"Scaricando clip {i+1}/{total_clips}...")
                
                clip = self.download_clip_from_timestamp(
                    video_url, 
                    timestamp_data['seconds'], 
                    clip_duration, 
                    url_hash, 
                    i
                )
                
                # Aggiungi descrizione
                if clip:
                    clip['description'] = timestamp_data['description']
                
                clips.append(clip)
            
            # Crea ZIP
            if progress_callback:
                progress_callback(85, "Creando pacchetto ZIP...")
            
            zip_path, successful_count = self.create_zip_package(clips, task_id)
            
            if progress_callback:
                progress_callback(100, "Completato!")
            
            # Calcola statistiche
            successful_clips = [c for c in clips if c.get('success')]
            total_size_mb = sum(c.get('size_mb', 0) for c in successful_clips)
            
            return {
                'success': True,
                'clips': clips,
                'successful_clips': successful_count,
                'total_clips': total_clips,
                'total_size_mb': total_size_mb,
                'zip_path': zip_path,
                'zip_filename': os.path.basename(zip_path) if zip_path else None,
                'download_url': f'/api/download/{task_id}' if zip_path else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Istanza globale dell'extractor
extractor = TimestampClipExtractor(TEMP_DIR)

def process_clips_async(video_url, timestamps_input, clip_duration, task_id):
    """Funzione asincrona per processare le clip"""
    
    def progress_callback(progress, message):
        task_progress[task_id] = {
            'progress': progress,
            'message': message,
            'status': 'processing'
        }
    
    try:
        result = extractor.extract_clips(
            video_url, 
            timestamps_input, 
            clip_duration, 
            task_id, 
            progress_callback
        )
        
        task_progress[task_id]['status'] = 'completed'
        task_results[task_id] = result
        
    except Exception as e:
        task_progress[task_id] = {
            'progress': 0,
            'message': f'Errore: {str(e)}',
            'status': 'failed',
            'error': str(e)
        }

# API ENDPOINTS

@app.route('/api/extract-clips', methods=['POST'])
def extract_clips_endpoint():
    """Endpoint principale per estrazione clip"""
    
    try:
        data = request.get_json()
        
        video_url = data.get('video_url', '').strip()
        timestamps_input = data.get('timestamps_input', '').strip()
        clip_duration = int(data.get('clip_duration', 60))
        
        if not video_url or not timestamps_input:
            return jsonify({
                'success': False,
                'error': 'URL video e timestamp sono richiesti'
            }), 400
        
        # Genera task ID unico
        task_id = str(uuid.uuid4())
        
        # Inizializza progress
        task_progress[task_id] = {
            'progress': 0,
            'message': 'Iniziando elaborazione...',
            'status': 'starting'
        }
        
        # Avvia processo asincrono
        thread = threading.Thread(
            target=process_clips_async,
            args=(video_url, timestamps_input, clip_duration, task_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Elaborazione avviata'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """Endpoint per ottenere il progresso di un task"""
    
    if task_id not in task_progress:
        return jsonify({
            'success': False,
            'error': 'Task non trovato'
        }), 404
    
    progress_data = task_progress[task_id].copy()
    
    # Se completato, aggiungi risultati
    if progress_data['status'] == 'completed' and task_id in task_results:
        progress_data['results'] = task_results[task_id]
    
    return jsonify(progress_data)

@app.route('/api/download/<task_id>', methods=['GET'])
def download_zip(task_id):
    """Endpoint per scaricare il ZIP delle clip"""
    
    if task_id not in task_results:
        return jsonify({
            'success': False,
            'error': 'Risultati non trovati'
        }), 404
    
    result = task_results[task_id]
    
    if not result.get('success') or not result.get('zip_path'):
        return jsonify({
            'success': False,
            'error': 'Nessun file da scaricare'
        }), 404
    
    zip_path = result['zip_path']
    
    if not os.path.exists(zip_path):
        return jsonify({
            'success': False,
            'error': 'File non trovato'
        }), 404
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=result.get('zip_filename', 'clips.zip'),
        mimetype='application/zip'
    )

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'temp_dir': TEMP_DIR
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Timestamp Clip Extractor API',
        'version': '1.0.0',
        'endpoints': [
            'POST /api/extract-clips',
            'GET /api/progress/<task_id>',
            'GET /api/download/<task_id>',
            'GET /api/health'
        ]
    })

if __name__ == '__main__':
    print("🚀 Avviando Timestamp Clip Extractor API...")
    print(f"📁 Directory temporanea: {TEMP_DIR}")
    
    app.run(debug=True, host='0.0.0.0', port=8000)
