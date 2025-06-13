import React, { useState } from 'react';
import { Upload, Download, Play, Clock, FileVideo, Loader, CheckCircle, XCircle } from 'lucide-react';

const TimestampClipExtractor = () => {
  const [videoUrl, setVideoUrl] = useState('');
  const [timestampInput, setTimestampInput] = useState(`0:15:43 Stream Time Marker - Momento epico
0:28:15 Stream Time Marker - Fail divertente  
0:45:30 Stream Time Marker - Highlight principale
1:02:45 Stream Time Marker - Reazione chat
1:18:20 Stream Time Marker - Boss fight finale`);
  const [clipDuration, setClipDuration] = useState(60);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [progress, setProgress] = useState(0);

  // API Base URL - usa localhost durante sviluppo
  const API_BASE = 'https://maat-production.up.railway.app';

  const parseTimestamps = (input) => {
    const pattern = /(\d+:\d+:\d+)\s+Stream Time Marker\s*-?\s*(.*)/g;
    const timestamps = [];
    let match;
    
    while ((match = pattern.exec(input)) !== null) {
      timestamps.push({
        original: match[1],
        description: match[2] || `Evento al ${match[1]}`
      });
    }
    
    return timestamps;
  };

  const processClips = async () => {
    if (!videoUrl.trim() || !timestampInput.trim()) {
      alert('⚠️ Compila tutti i campi!');
      return;
    }

    const timestamps = parseTimestamps(timestampInput);
    if (timestamps.length === 0) {
      alert('⚠️ Nessun timestamp "Stream Time Marker" trovato!');
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setResults(null);

    try {
      // 1. Avvia processo
      const response = await fetch(`${API_BASE}/api/extract-clips`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_url: videoUrl,
          timestamps_input: timestampInput,
          clip_duration: clipDuration
        })
      });

      if (!response.ok) {
        throw new Error(`Errore: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.task_id) {
        // 2. Polling per progress
        pollProgress(data.task_id);
      } else {
        // Risultato immediato
        setResults(data);
        setIsProcessing(false);
      }

    } catch (error) {
      console.error('Errore:', error);
      alert(`Errore durante l'elaborazione: ${error.message}`);
      setIsProcessing(false);
    }
  };

  const pollProgress = async (taskId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/progress/${taskId}`);
        const data = await response.json();
        
        setProgress(data.progress || 0);
        
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setResults(data.results);
          setIsProcessing(false);
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          alert('Elaborazione fallita: ' + data.error);
          setIsProcessing(false);
        }
      } catch (error) {
        console.error('Errore polling:', error);
      }
    }, 2000);

    // Timeout dopo 10 minuti
    setTimeout(() => {
      clearInterval(pollInterval);
      if (isProcessing) {
        setIsProcessing(false);
        alert('Timeout elaborazione');
      }
    }, 600000);
  };

  const downloadZip = async () => {
    if (!results?.download_url) return;
    
    try {
      const response = await fetch(`${API_BASE}${results.download_url}`);
      const blob = await response.blob();
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = results.zip_filename || 'timestamp_clips.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert('Errore download: ' + error.message);
    }
  };

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` 
                 : `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-800">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-white mb-4">
            🎬 Timestamp Clip Extractor
          </h1>
          <p className="text-xl text-purple-100">
            Estrai clip precise dai tuoi stream usando i timestamp
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {/* Input Form */}
          <div className="bg-white rounded-2xl shadow-2xl p-8 mb-8">
            <div className="grid gap-6">
              {/* Video URL */}
              <div>
                <label className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                  <Play className="mr-2 text-purple-600" size={20} />
                  URL Video (Twitch/YouTube)
                </label>
                <input
                  type="url"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  placeholder="https://www.twitch.tv/videos/..."
                  className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-all"
                  disabled={isProcessing}
                />
              </div>

              {/* Timestamp Input */}
              <div>
                <label className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                  <Clock className="mr-2 text-purple-600" size={20} />
                  Timestamp Input
                </label>
                <textarea
                  value={timestampInput}
                  onChange={(e) => setTimestampInput(e.target.value)}
                  placeholder="0:15:43 Stream Time Marker - Descrizione evento"
                  className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-all font-mono text-sm"
                  rows={6}
                  disabled={isProcessing}
                />
                <p className="text-sm text-gray-500 mt-2">
                  📝 Formato: "HH:MM:SS Stream Time Marker - Descrizione"
                </p>
              </div>

              {/* Clip Duration */}
              <div>
                <label className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                  <FileVideo className="mr-2 text-purple-600" size={20} />
                  Durata Clip (secondi)
                </label>
                <input
                  type="number"
                  value={clipDuration}
                  onChange={(e) => setClipDuration(parseInt(e.target.value))}
                  min="10"
                  max="300"
                  className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-all"
                  disabled={isProcessing}
                />
                <p className="text-sm text-gray-500 mt-2">
                  ⏰ La clip inizierà {clipDuration} secondi prima del timestamp
                </p>
              </div>

              {/* Process Button */}
              <button
                onClick={processClips}
                disabled={isProcessing}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 px-8 rounded-xl font-bold text-lg hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isProcessing ? (
                  <>
                    <Loader className="animate-spin mr-2" size={20} />
                    Elaborazione in corso... {progress}%
                  </>
                ) : (
                  <>
                    <Upload className="mr-2" size={20} />
                    🚀 Estrai Clip
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          {isProcessing && (
            <div className="bg-white rounded-xl p-6 mb-8">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Progresso</span>
                <span className="text-sm font-medium text-gray-700">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-gradient-to-r from-purple-600 to-blue-600 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Results */}
          {results && (
            <div className="bg-white rounded-2xl shadow-2xl p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                <CheckCircle className="mr-2 text-green-500" size={24} />
                Risultati Elaborazione
              </h2>

              {/* Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="bg-gradient-to-r from-green-500 to-emerald-500 text-white p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold">{results.successful_clips || 0}</div>
                  <div className="text-sm opacity-90">Clip Riuscite</div>
                </div>
                <div className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold">{results.total_size_mb?.toFixed(1) || '0.0'} MB</div>
                  <div className="text-sm opacity-90">Dimensione Totale</div>
                </div>
                <div className="bg-gradient-to-r from-purple-500 to-indigo-500 text-white p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold">{(results.successful_clips || 0) * clipDuration}s</div>
                  <div className="text-sm opacity-90">Durata Totale</div>
                </div>
              </div>

              {/* Download Button */}
              {results.download_url && (
                <div className="text-center mb-8">
                  <button
                    onClick={downloadZip}
                    className="bg-gradient-to-r from-green-500 to-emerald-500 text-white py-3 px-8 rounded-xl font-bold text-lg hover:from-green-600 hover:to-emerald-600 transition-all flex items-center mx-auto"
                  >
                    <Download className="mr-2" size={20} />
                    📥 Scarica ZIP con tutte le clip
                  </button>
                </div>
              )}

              {/* Clip Details */}
              {results.clips && results.clips.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold text-gray-700 mb-4">📹 Dettagli Clip</h3>
                  {results.clips.map((clip, index) => (
                    <div key={index} className="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-all">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-semibold text-lg text-gray-800 mb-2 flex items-center">
                            {clip.success ? (
                              <CheckCircle className="mr-2 text-green-500" size={18} />
                            ) : (
                              <XCircle className="mr-2 text-red-500" size={18} />
                            )}
                            Clip #{index + 1}
                          </h4>
                          {clip.success ? (
                            <div className="text-sm text-gray-600 space-y-1">
                              <p><strong>File:</strong> {clip.filename}</p>
                              <p><strong>Timestamp:</strong> {formatTime(clip.timestamp)}</p>
                              <p><strong>Inizio clip:</strong> {formatTime(clip.start_time)}</p>
                              <p><strong>Dimensione:</strong> {clip.size_mb?.toFixed(1)} MB</p>
                              {clip.description && <p><strong>Descrizione:</strong> {clip.description}</p>}
                            </div>
                          ) : (
                            <p className="text-red-600 text-sm">❌ Download fallito</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TimestampClipExtractor;
