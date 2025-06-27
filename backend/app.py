# app.py - Backend Flask per Timestamp Clip Extractor
import os
import json
import threading
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import subprocess
import re
import hashlib
import zipfile
import tempfile
import shutil
from dotenv import load_dotenv
import openai

# Carica variabili ambiente
load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:3000',
    'http://localhost:5173',
    'https://new-maat.vercel.app',
    'https://maat-frontend-2c0n0g1s1-christians-projects-75053e23.vercel.app'
])  # Enable CORS for frontend

# Configurazione Database e JWT
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///maat_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'maat-secret-key-change-in-production'

# Inizializza estensioni
from models import db
db.init_app(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# Configura OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Importa blueprint autenticazione
from auth import auth_bp

# Registra blueprint
app.register_blueprint(auth_bp, url_prefix='/api/auth')

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
        
        # Verifica OpenAI API key
        if not openai.api_key:
            print("⚠️ ATTENZIONE: OPENAI_API_KEY non configurata - sottotitoli disabilitati")
        else:
            print("✅ OpenAI API key configurata")
        
        print("✅ Setup completato!")

    def generate_subtitles(self, video_file):
        """Genera sottotitoli usando OpenAI Whisper API"""
        try:
            if not openai.api_key:
                print("  ⚠️ API key OpenAI mancante - saltando sottotitoli")
                return None
                
            print(f"  📝 Generando sottotitoli con OpenAI per {os.path.basename(video_file)}...")
            
            # Controlla dimensione file (limite OpenAI: 25MB)
            file_size = os.path.getsize(video_file)
            if file_size > 25 * 1024 * 1024:  # 25MB
                print(f"  ⚠️ File troppo grande ({file_size/1024/1024:.1f}MB) - saltando sottotitoli")
                return None
            
            # Chiamata API OpenAI Whisper
            with open(video_file, 'rb') as audio_file:
                response = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="srt"
                )
            
            # Salva file SRT
            srt_file = video_file.replace('.mp4', '.srt')
            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write(response)
            
            print(f"    ✅ Sottotitoli salvati: {os.path.basename(srt_file)}")
            return srt_file
            
        except openai.APIError as e:
            print(f"    ❌ Errore API OpenAI: {e}")
            return None
        except Exception as e:
            print(f"    ❌ Errore generazione sottotitoli: {e}")
            return None

    def seconds_to_srt_time(self, seconds):
        """Converte secondi in formato SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
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
        """Estrae timestamp da testo formattato o formato semplice"""
        print("📋 Parsing timestamp...")
        
        # Controlla se è formato "Stream Time Marker"
        if "Stream Time Marker" in timestamps_text:
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
        
        # Formato semplice: "0:01-0:03,0:05-0:07" 
        else:
            timestamps = []
            ranges = timestamps_text.split(',')
            
            for i, range_str in enumerate(ranges):
                range_str = range_str.strip()
                if '-' in range_str:
                    start_str, end_str = range_str.split('-', 1)
                    try:
                        start_seconds = self.parse_timestamp(start_str.strip())
                        end_seconds = self.parse_timestamp(end_str.strip())
                        # Usa il momento centrale del range
                        timestamp_seconds = (start_seconds + end_seconds) // 2
                        timestamps.append({
                            'original': range_str,
                            'seconds': timestamp_seconds,
                            'description': f"Clip {i+1}"
                        })
                    except ValueError as e:
                        print(f"⚠️ Errore range {range_str}: {e}")
            
            print(f"✅ Trovati {len(timestamps)} timestamp validi")
            return timestamps
    
    def download_clip_from_timestamp(self, video_url, timestamp_seconds, clip_duration=60, url_hash="", clip_index=0, social_formats=None, subtitles_enabled=False):
        """Scarica clip da timestamp specifico"""
        
        start_time = max(0, timestamp_seconds - clip_duration)
        
        timestamp_min = timestamp_seconds // 60
        timestamp_sec = timestamp_seconds % 60
        
        # File base (originale)
        base_output_file = os.path.join(
            self.temp_dir, 
            f"temp_base_{url_hash}_{clip_index+1}_{timestamp_min:02d}m{timestamp_sec:02d}s.mp4"
        )
        
        # Comando per scaricare clip base
        cmd = [
            'yt-dlp',
            '--no-check-certificates',
            '-f', 'best[height<=720]',  # Ottimizzato per trial
            '--external-downloader', 'ffmpeg',
            '--external-downloader-args', f'ffmpeg:-ss {start_time} -t {clip_duration}',
            '-o', base_output_file,
            video_url
        ]        
        
        try:
            # Scarica clip base
            print(f"  ⬇️ Scaricando clip base...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode != 0 or not os.path.exists(base_output_file):
                print(f"  ❌ Errore download clip base")
                print(f"  Error: {result.stderr}")
                return {
                    'success': False,
                    'timestamp': timestamp_seconds,
                    'error': result.stderr
                }
            
            # Genera sottotitoli se richiesti
            srt_file = None
            if subtitles_enabled:
                print(f"  📝 Generando sottotitoli...")
                srt_file = self.generate_subtitles(base_output_file)
                if srt_file:
                    print(f"    ✅ Sottotitoli generati")
                else:
                    print(f"    ⚠️ Sottotitoli non disponibili")
            
            # Genera formati social
            social_files = []
            total_size = 0
            
            if social_formats is None:
                social_formats = {'youtube': True}  # Default
            
            # TikTok - 9:16 verticale
            if social_formats.get('tiktok', False):
                tiktok_file = os.path.join(
                    self.temp_dir,
                    f"tiktok_{url_hash}_{clip_index+1}_{timestamp_min:02d}m{timestamp_sec:02d}s.mp4"
                )
                
                # Comando TikTok ottimizzato
                if srt_file and os.path.exists(srt_file):
                    # Con sottotitoli stilizzati
                    tiktok_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', f'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,subtitles={srt_file}:force_style=\'FontSize=18,BackColour=&H80000000,Bold=1,Alignment=2,MarginV=40\'',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'copy', '-y', tiktok_file
                    ]
                    print(f"    🎬 TikTok con sottotitoli stilizzati (720p ottimizzato)")
                else:
                    # Senza sottotitoli - OTTIMIZZATO
                    tiktok_cmd = [
                       'ffmpeg', '-i', base_output_file,
                       '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black',
                       '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                       '-c:a', 'copy', '-y', tiktok_file
                    ]
                    print(f"    🎬 TikTok senza sottotitoli (720p ottimizzato)")
                    
                tiktok_result = subprocess.run(tiktok_cmd, capture_output=True, text=True)
                if tiktok_result.returncode == 0 and os.path.exists(tiktok_file):
                    size_mb = os.path.getsize(tiktok_file) / (1024*1024)
                    total_size += size_mb
                    social_files.append({
                        'format': 'TikTok (720p)',
                        'file': tiktok_file,
                        'filename': os.path.basename(tiktok_file),
                        'size_mb': size_mb
                    })
                    print(f"    ✅ TikTok: {size_mb:.1f} MB")
            
            # Instagram - 1:1 quadrato
            if social_formats.get('instagram', False):
                instagram_file = os.path.join(
                    self.temp_dir,
                    f"instagram_{url_hash}_{clip_index+1}_{timestamp_min:02d}m{timestamp_sec:02d}s.mp4"
                )
                
                # Comando Instagram ottimizzato
                if srt_file and os.path.exists(srt_file):
                    instagram_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', f'scale=720:720:force_original_aspect_ratio=decrease,pad=720:720:(ow-iw)/2:(oh-ih)/2:black,subtitles={srt_file}:force_style=\'FontSize=16,BackColour=&H80000000,Bold=1,Alignment=2,MarginV=30\'',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'copy', '-y', instagram_file
                    ]
                    print(f"    🎬 Instagram con sottotitoli (720p ottimizzato)")
                else:
                    instagram_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', 'scale=720:720:force_original_aspect_ratio=decrease,pad=720:720:(ow-iw)/2:(oh-ih)/2:black',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'copy', '-y', instagram_file
                    ]
                    print(f"    🎬 Instagram senza sottotitoli (720p ottimizzato)")
                
                instagram_result = subprocess.run(instagram_cmd, capture_output=True, text=True)
                if instagram_result.returncode == 0 and os.path.exists(instagram_file):
                    size_mb = os.path.getsize(instagram_file) / (1024*1024)
                    total_size += size_mb
                    social_files.append({
                        'format': 'Instagram (720p)',
                        'file': instagram_file,
                        'filename': os.path.basename(instagram_file),
                        'size_mb': size_mb
                    })
                    print(f"    ✅ Instagram: {size_mb:.1f} MB")
            
            # Facebook - 16:9 orizzontale
            if social_formats.get('facebook', False):
                facebook_file = os.path.join(
                    self.temp_dir,
                    f"facebook_{url_hash}_{clip_index+1}_{timestamp_min:02d}m{timestamp_sec:02d}s.mp4"
                )
                
                # Comando Facebook ottimizzato
                if srt_file and os.path.exists(srt_file):
                    facebook_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,subtitles={srt_file}:force_style=\'FontSize=14,BackColour=&H80000000,Bold=1,Alignment=2,MarginV=50\'',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'copy', '-y', facebook_file
                    ]
                    print(f"    🎬 Facebook con sottotitoli (720p ottimizzato)")
                else:
                    facebook_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'copy', '-y', facebook_file
                    ]
                    print(f"    🎬 Facebook senza sottotitoli (720p ottimizzato)")
                
                facebook_result = subprocess.run(facebook_cmd, capture_output=True, text=True)
                if facebook_result.returncode == 0 and os.path.exists(facebook_file):
                    size_mb = os.path.getsize(facebook_file) / (1024*1024)
                    total_size += size_mb
                    social_files.append({
                        'format': 'Facebook (720p)',
                        'file': facebook_file,
                        'filename': os.path.basename(facebook_file),
                        'size_mb': size_mb
                    })
                    print(f"    ✅ Facebook: {size_mb:.1f} MB")
            
            # YouTube - 16:9 HD ottimizzato
            if social_formats.get('youtube', False):
                youtube_file = os.path.join(
                    self.temp_dir,
                    f"youtube_{url_hash}_{clip_index+1}_{timestamp_min:02d}m{timestamp_sec:02d}s.mp4"
                )
                
                # Comando YouTube ottimizzato
                if srt_file and os.path.exists(srt_file):
                    youtube_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,subtitles={srt_file}:force_style=\'FontSize=16,BackColour=&H80000000,Bold=1,Alignment=2,MarginV=60\'',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'aac', '-b:a', '128k', '-y', youtube_file
                    ]
                    print(f"    🎬 YouTube con sottotitoli (720p ottimizzato)")
                else:
                    youtube_cmd = [
                        'ffmpeg', '-i', base_output_file,
                        '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                        '-c:a', 'aac', '-b:a', '128k', '-y', youtube_file
                    ]
                    print(f"    🎬 YouTube senza sottotitoli (720p ottimizzato)")
                
                youtube_result = subprocess.run(youtube_cmd, capture_output=True, text=True)
                if youtube_result.returncode == 0 and os.path.exists(youtube_file):
                    size_mb = os.path.getsize(youtube_file) / (1024*1024)
                    total_size += size_mb
                    social_files.append({
                        'format': 'YouTube (720p)',
                        'file': youtube_file,
                        'filename': os.path.basename(youtube_file),
                        'size_mb': size_mb
                    })
                    print(f"    ✅ YouTube: {size_mb:.1f} MB")
            
            # Rimuovi file temporanei
            if os.path.exists(base_output_file):
                os.remove(base_output_file)
            if srt_file and os.path.exists(srt_file):
                os.remove(srt_file)
            
            if social_files:
                subtitle_status = " con sottotitoli" if srt_file else " senza sottotitoli"
                print(f"  ✅ Clip {clip_index+1}{subtitle_status} - Generati {len(social_files)} formati ({total_size:.1f} MB totali)")
                return {
                    'success': True,
                    'social_files': social_files,
                    'timestamp': timestamp_seconds,
                    'start_time': start_time,
                    'duration': clip_duration,
                    'size_mb': total_size,
                    'formats_count': len(social_files),
                    'has_subtitles': bool(srt_file)
                }
            else:
                print(f"  ❌ Nessun formato generato per clip {clip_index+1}")
                return {
                    'success': False,
                    'timestamp': timestamp_seconds,
                    'error': 'Nessun formato social selezionato o errori nella conversione'
                }
                
        except subprocess.TimeoutExpired:
            print(f"  ⏰ Timeout clip {clip_index+1}")
            return {
                'success': False,
                'timestamp': timestamp_seconds,
                'error': 'Timeout'
            }
        except Exception as e:
            print(f"  ❌ Errore generico clip {clip_index+1}: {str(e)}")
            return {
                'success': False,
                'timestamp': timestamp_seconds,
                'error': str(e)
            }

    def create_zip_package(self, clips, task_id):
        """Crea ZIP con tutte le clip riuscite"""
        
        zip_filename = f"timestamp_clips_{task_id}.zip"
        zip_path = os.path.join(self.temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            files_added = 0
            
            for clip in clips:
                if clip.get('success') and clip.get('social_files'):
                    # Aggiungi tutti i file social della clip
                    for social_file in clip['social_files']:
                        if os.path.exists(social_file['file']):
                            # Nome file con prefisso formato
                            zip_name = f"{social_file['format'].replace(' ', '_').replace('(', '').replace(')', '')}_{social_file['filename']}"
                            zipf.write(social_file['file'], zip_name)
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
    
    def extract_clips(self, video_url, timestamps_input, clip_duration, task_id, social_formats=None, subtitles_enabled=False, progress_callback=None):
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
                    subtitle_msg = " con sottotitoli" if subtitles_enabled else ""
                    progress_callback(int(progress), f"Scaricando clip {i+1}/{total_clips}{subtitle_msg}...")
                
                clip = self.download_clip_from_timestamp(
                    video_url, 
                    timestamp_data['seconds'], 
                    clip_duration, 
                    url_hash, 
                    i,
                    social_formats,
                    subtitles_enabled
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
            total_size_mb = 0
            total_files = 0
            clips_with_subtitles = 0
            
            for clip in successful_clips:
                if clip.get('social_files'):
                    total_size_mb += clip.get('size_mb', 0)
                    total_files += len(clip.get('social_files', []))
                    if clip.get('has_subtitles'):
                        clips_with_subtitles += 1
            
            return {
                'success': True,
                'clips': clips,
                'successful_clips': len(successful_clips),
                'total_files': total_files,
                'total_clips': total_clips,
                'total_size_mb': total_size_mb,
                'clips_with_subtitles': clips_with_subtitles,
                'subtitles_enabled': subtitles_enabled,
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

def process_clips_async(video_url, timestamps_input, clip_duration, task_id, social_formats, subtitles_enabled):
    """Funzione asincrona per processare le clip"""
    
    print(f"🚀 AVVIO PROCESSO ASINCRONO - Task ID: {task_id}")
    print(f"📹 Video URL: {video_url}")
    print(f"📋 Timestamps: {timestamps_input[:100]}...")
    print(f"🎯 Formati: {social_formats}")
    print(f"📝 Sottotitoli: {'ATTIVI' if subtitles_enabled else 'DISATTIVI'}")
    
    def progress_callback(progress, message):
        print(f"📊 Progress: {progress}% - {message}")
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
            social_formats,
            subtitles_enabled,
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
        social_formats = data.get('social_formats', {
            'tiktok': True,
            'instagram': True, 
            'facebook': True,
            'youtube': True
        })
        subtitles_enabled = data.get('subtitles_enabled', False)
        
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
        print(f"🔥 STO PER AVVIARE IL THREAD - Task ID: {task_id}")
        print(f"🔥 Parametri: URL={video_url[:50]}, Durata={clip_duration}")
        print(f"🔥 Formati ricevuti: {social_formats}")
        print(f"🔥 Sottotitoli: {subtitles_enabled}")
        
        thread = threading.Thread(
            target=process_clips_async,
            args=(video_url, timestamps_input, clip_duration, task_id, social_formats, subtitles_enabled)
        )
        thread.daemon = True
        thread.start()
        
        print(f"🔥 THREAD AVVIATO!")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Elaborazione avviata',
            'subtitles_enabled': subtitles_enabled
        })
        
    except Exception as e:
        print(f"❌ ERRORE nell'endpoint: {str(e)}")
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
        'temp_dir': TEMP_DIR,
        'openai_configured': bool(openai.api_key)
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Timestamp Clip Extractor API',
        'version': '1.0.1',
        'features': {
            'subtitles': bool(openai.api_key),
            'openai_whisper': True
        },
        'endpoints': [
            'POST /api/extract-clips',
            'GET /api/progress/<task_id>',
            'GET /api/download/<task_id>',
            'GET /api/health'
        ]
    })

@app.route('/api/test-auth', methods=['GET'])
def test_auth():
    return jsonify({'message': 'Auth endpoint test', 'status': 'working'})

# Inizializza database
with app.app_context():
    db.create_all()
    print("✅ Database tabelle create")

if __name__ == '__main__':
    print("🚀 Avviando Timestamp Clip Extractor API...")
    print(f"📁 Directory temporanea: {TEMP_DIR}")
    print(f"📝 Sottotitoli OpenAI: {'✅ ATTIVI' if openai.api_key else '❌ DISATTIVI (API key mancante)'}")
    
    app.run(debug=True, host='0.0.0.0', port=8000)
