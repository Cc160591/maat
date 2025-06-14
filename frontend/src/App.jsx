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
    <div className="min-h-screen relative overflow-hidden bg-red-500">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-800">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white rounded-full mix-blend-multiply filter blur-xl animate-pulse"></div>
          <div className="absolute top-3/4 right-1/4 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl animate-pulse animation-delay-2000"></div>
          <div className="absolute bottom-1/4 left-1/2 w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl animate-pulse animation-delay-4000"></div>
        </div>
      </div>

      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="backdrop-filter backdrop-blur-lg bg-white bg-opacity-10 border border-white border-opacity-20 rounded-3xl p-8 mx-auto max-w-2xl shadow-2xl">
            <h1 className="text-5xl font-bold text-white mb-4 drop-shadow-lg">
              🎬 MAAT
            </h1>
            <p className="text-xl text-white text-opacity-90 drop-shadow">
              Estrai clip precise dai tuoi stream usando i timestamp
            </p>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {/* Input Form */}
          <div className="backdrop-filter backdrop-blur-xl bg-white bg-opacity-10 border border-white border-opacity-20 rounded-3xl shadow-2xl p-8 mb-8 relative overflow-hidden">
            {/* Shimmer effect */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-white via-opacity-30 to-transparent animate-pulse"></div>
            
            <div className="grid gap-6">
              {/* Video URL */}
              <div>
                <label className="flex items-center text-lg font-semibold text-white text-opacity-90 mb-3">
                  <Play className="mr-2 text-white" size={20} />
                  URL Video (Twitch/YouTube)
                </label>
                <input
                  type="url"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  placeholder="https://www.twitch.tv/videos/..."
                  className="w-full p-4 backdrop-filter backdrop-blur-md bg-white bg-opacity-10 border border-white border-opacity-30 rounded-xl focus:bg-opacity-20 focus:border-opacity-50 focus:outline-none transition-all text-white placeholder-white placeholder-opacity-50"
                  disabled={isProcessing}
                />
              </div>

              {/* Timestamp Input */}
              <div>
                <label className="flex items-center text-lg font-semibold text-white text-opacity-90 mb-3">
                  <Clock className="mr-2 text-white" size={20} />
                  Timestamp Input
                </label>
                <textarea
                  value={timestampInput}
                  onChange={(e) => setTimestampInput(e.target.value)}
                  placeholder="0:15:43 Stream Time Marker - Descrizione evento"
                  className="w-full p-4 backdrop-filter backdrop-blur-md bg-white bg-opacity-10 border border-white border-opacity-30 rounded-xl focus:bg-opacity-20 focus:border-opacity-50 focus:outline-none transition-all font-mono text-sm text-white placeholder-white placeholder-opacity-50 resize-none"
                  rows={6}
                  disabled={isProcessing}
                />
                <p className="text-sm text-white text-opacity-70 mt-2">
                  📝 Formato: "HH:MM:SS Stream Time Marker - Descrizione"
                </p>
              </div>

              {/* Clip Duration */}
              <div>
                <label className="flex items-center text-lg font-semibold text-white text-opacity-90 mb-3">
                  <FileVideo className="mr-2 text-white" size={20} />
                  Durata Clip (secondi)
                </label>
                <input
                  type="number"
                  value={clipDuration}
                  onChange={(e) => setClipDuration(parseInt(e.target.value))}
                  min="10"
                  max="300"
                  className="w-full p-4 backdrop-filter backdrop-blur-md bg-white bg-opacity-10 border border-white border-opacity-30 rounded-xl focus:bg-opacity-20 focus:border-opacity-50 focus:outline-none transition-all text-white placeholder-white placeholder-opacity-50"
                  disabled={isProcessing}
                />
                <p className="text-sm text-white text-opacity-70 mt-2">
                  ⏰ La clip inizierà {clipDuration} secondi prima del timestamp
                </p>
              </div>

              {/* Process Button */}
              <button
                onClick={processClips}
                disabled={isProcessing}
                className="w-full backdrop-filter backdrop-blur-md bg-gradient-to-r from-white from-opacity-20 to-white to-opacity-10 border border-white border-opacity-30 text-white py-4 px-8 rounded-xl font-bold text-lg hover:bg-opacity-30 hover:shadow-2xl hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-purple-400 to-blue-400 opacity-20 rounded-xl"></div>
                <div className="relative z-10 flex items-center">
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
                </div>
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          {isProcessing && (
            <div className="backdrop-filter backdrop-blur-xl bg-white bg-opacity-10 border border-white border-opacity-20 rounded-2xl p-6 mb-8">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-white text-opacity-90">Progresso</span>
                <span className="text-sm font-medium text-white text-opacity-90">{progress}%</span>
              </div>
              <div className="w-full backdrop-filter backdrop-blur-md bg-white bg-opacity-10 rounded-full h-4 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-green-400 to-blue-400 h-4 rounded-full transition-all duration-500 relative overflow-hidden"
                  style={{ width: `${progress}%` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white via-opacity-20 to-transparent animate-pulse"></div>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {results && (
            <div className="backdrop-filter backdrop-blur-xl bg-white bg-opacity-10 border border-white border-opacity-20 rounded-3xl shadow-2xl p-8 relative overflow-hidden">
              {/* Shimmer effect */}
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-green-400 via-opacity-60 to-transparent"></div>
              
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
                <CheckCircle className="mr-2 text-green-400" size={24} />
                Risultati Elaborazione
              </h2>

              {/* Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="backdrop-filter backdrop-blur-md bg-gradient-to-r from-green-400 from-opacity-20 to-emerald-400 to-opacity-20 border border-green-400 border-opacity-30 text-white p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold">{results.successful_clips || 0}</div>
                  <div className="text-sm opacity-90">Clip Riuscite</div>
                </div>
                <div className="backdrop-filter backdrop-blur-md bg-gradient-to-r from-blue-400 from-opacity-20 to-cyan-400 to-opacity-20 border border-blue-400 border-opacity-30 text-white p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold">{results.total_size_mb?.toFixed(1) || '0.0'} MB</div>
                  <div className="text-sm opacity-90">Dimensione Totale</div>
                </div>
                <div className="backdrop-filter backdrop-blur-md bg-gradient-to-r from-purple-400 from-opacity-20 to-indigo-400 to-opacity-20 border border-purple-400 border-opacity-30 text-white p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold">{(results.successful_clips || 0) * clipDuration}s</div>
                  <div className="text-sm opacity-90">Durata Totale</div>
                </div>
              </div>

              {/* Download Button */}
              {results.download_url && (
                <div className="text-center mb-8">
                  <button
                    onClick={downloadZip}
                    className="backdrop-filter backdrop-blur-md bg-gradient-to-r from-green-400 from-opacity-20 to-emerald-400 to-opacity-20 border border-green-400 border-opacity-40 text-white py-3 px-8 rounded-xl font-bold text-lg hover:bg-opacity-30 hover:shadow-2xl hover:scale-105 transition-all flex items-center mx-auto"
                  >
                    <Download className="mr-2" size={20} />
                    📥 Scarica ZIP con tutte le clip
                  </button>
                </div>
              )}

              {/* Clip Details */}
              {results.clips && results.clips.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold text-white text-opacity-90 mb-4">📹 Dettagli Clip</h3>
                  {results.clips.map((clip, index) => (
                    <div key={index} className="backdrop-filter backdrop-blur-md bg-white bg-opacity-5 border border-white border-opacity-20 rounded-xl p-4 hover:bg-opacity-10 hover:shadow-lg transition-all">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-semibold text-lg text-white mb-2 flex items-center">
                            {clip.success ? (
                              <CheckCircle className="mr-2 text-green-400" size={18} />
                            ) : (
                              <XCircle className="mr-2 text-red-400" size={18} />
                            )}
                            Clip #{index + 1}
                          </h4>
                          {clip.success ? (
                            <div className="text-sm text-white text-opacity-80 space-y-1">
                              <p><strong>File:</strong> {clip.filename}</p>
                              <p><strong>Timestamp:</strong> {formatTime(clip.timestamp)}</p>
                              <p><strong>Inizio clip:</strong> {formatTime(clip.start_time)}</p>
                              <p><strong>Dimensione:</strong> {clip.size_mb?.toFixed(1)} MB</p>
                              {clip.description && <p><strong>Descrizione:</strong> {clip.description}</p>}
                            </div>
                          ) : (
                            <p className="text-red-400 text-sm">❌ Download fallito</p>
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
