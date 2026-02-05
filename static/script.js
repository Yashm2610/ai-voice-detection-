(function () {
  'use strict';

  // If page is loaded over http(s), use same origin (relative URL) so API always matches.
  // If opened as file (file://), point to localhost so user can try after starting server.
  var origin = window.location.origin;
  var isServedFromServer = origin && origin !== 'null' && origin.indexOf('file') !== 0;
  var API_KEY = 'team_hcl_2026_key';
  var SERVER_URL = 'http://127.0.0.1:8000';
  var API_URL = isServedFromServer ? '/api/detect-voice' : (SERVER_URL + '/api/detect-voice');

  // Show banner if opened as file (file://) so user opens from server
  (function () {
    var banner = document.getElementById('connectionBanner');
    var link = document.getElementById('connectionBannerLink');
    if (banner && (!origin || origin === 'null' || origin.indexOf('file') === 0)) {
      banner.hidden = false;
      document.body.classList.add('has-connection-banner');
      if (link) link.href = SERVER_URL;
    }
  })();

  var recordBtn = document.getElementById('recordBtn');
  var recordingStatus = document.getElementById('recordingStatus');
  var fileInput = document.getElementById('fileInput');
  var dropZone = document.getElementById('dropZone');
  var selectedFile = document.getElementById('selectedFile');
  var fileName = document.getElementById('fileName');
  var clearFile = document.getElementById('clearFile');
  var analyzeBtn = document.getElementById('analyzeBtn');
  var resultsPlaceholder = document.getElementById('resultsPlaceholder');
  var resultsContent = document.getElementById('resultsContent');
  var resultsError = document.getElementById('resultsError');
  var resultsErrorText = document.getElementById('resultsErrorText');
  var resultLanguage = document.getElementById('resultLanguage');
  var resultType = document.getElementById('resultType');
  var resultConfidence = document.getElementById('resultConfidence');

  var mediaRecorder = null;
  var recordedChunks = [];
  var currentAudioBlob = null;
  var currentAudioFile = null;
  var stream = null;

  // ----- Tabs -----
  document.querySelectorAll('.tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var targetId = tab.getAttribute('data-tab') === 'record' ? 'record-panel' : 'upload-panel';
      document.querySelectorAll('.tab').forEach(function (t) { t.classList.remove('active'); });
      document.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
      tab.classList.add('active');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // ----- Recording -----
  function setRecordingUI(recording) {
    recordBtn.classList.toggle('recording', recording);
    if (recordingStatus) recordingStatus.hidden = !recording;
  }

  function startRecording() {
    recordedChunks = [];
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(function (s) {
        stream = s;
        mediaRecorder = new MediaRecorder(s);
        mediaRecorder.ondataavailable = function (e) {
          if (e.data.size > 0) recordedChunks.push(e.data);
        };
        mediaRecorder.onstop = function () {
          if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
          stream = null;
          if (recordedChunks.length) {
            currentAudioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
            currentAudioFile = null;
            updateAnalyzeButton();
          }
          setRecordingUI(false);
        };
        mediaRecorder.start();
        setRecordingUI(true);
      })
      .catch(function () {
        alert('Microphone access is needed to record.');
      });
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  }

  recordBtn.addEventListener('click', function () {
    if (recordBtn.classList.contains('recording')) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  recordBtn.addEventListener('mousedown', function (e) {
    if (e.button !== 0) return;
    if (!recordBtn.classList.contains('recording')) startRecording();
  });
  recordBtn.addEventListener('mouseup', function () {
    if (recordBtn.classList.contains('recording')) stopRecording();
  });
  recordBtn.addEventListener('mouseleave', function () {
    if (recordBtn.classList.contains('recording')) stopRecording();
  });

  // ----- File upload -----
  function handleFile(file) {
    if (!file || !file.type.startsWith('audio/')) {
      return;
    }
    currentAudioFile = file;
    currentAudioBlob = null;
    fileName.textContent = file.name;
    selectedFile.hidden = false;
    updateAnalyzeButton();
  }

  fileInput.addEventListener('change', function () {
    var file = fileInput.files[0];
    handleFile(file);
  });

  clearFile.addEventListener('click', function () {
    currentAudioFile = null;
    currentAudioBlob = null;
    fileInput.value = '';
    selectedFile.hidden = true;
    hideError();
    showPlaceholder();
    updateAnalyzeButton();
  });

  dropZone.addEventListener('click', function () {
    fileInput.click();
  });

  dropZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', function () {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    var file = e.dataTransfer.files[0];
    handleFile(file);
  });

  function hasAudio() {
    return currentAudioBlob != null || currentAudioFile != null;
  }

  function updateAnalyzeButton() {
    analyzeBtn.disabled = !hasAudio();
  }

  // ----- Convert any audio to WAV (backend expects soundfile-readable format) -----
  function arrayBufferToBase64(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = '';
    for (var i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  function writeWavHeader(dataView, numChannels, sampleRate, numSamples) {
    var byteRate = sampleRate * numChannels * 2;
    var blockAlign = numChannels * 2;
    var dataSize = numSamples * blockAlign;
    dataView.setUint8(0, 0x52); dataView.setUint8(1, 0x49); dataView.setUint8(2, 0x46); dataView.setUint8(3, 0x46);
    dataView.setUint32(4, 36 + dataSize, true);
    dataView.setUint8(8, 0x57); dataView.setUint8(9, 0x41); dataView.setUint8(10, 0x56); dataView.setUint8(11, 0x45);
    dataView.setUint8(12, 0x66); dataView.setUint8(13, 0x6d); dataView.setUint8(14, 0x74); dataView.setUint8(15, 0x20);
    dataView.setUint32(16, 16, true);
    dataView.setUint16(20, 1, true);
    dataView.setUint16(22, numChannels, true);
    dataView.setUint32(24, sampleRate, true);
    dataView.setUint32(28, byteRate, true);
    dataView.setUint16(32, blockAlign, true);
    dataView.setUint16(34, 16, true);
    dataView.setUint8(36, 0x64); dataView.setUint8(37, 0x61); dataView.setUint8(38, 0x74); dataView.setUint8(39, 0x61);
    dataView.setUint32(40, dataSize, true);
  }

  function audioBufferToWav(buffer) {
    var numChannels = buffer.numberOfChannels;
    var sampleRate = buffer.sampleRate;
    var length = buffer.length * numChannels;
    var numSamples = buffer.length;
    var wav = new ArrayBuffer(44 + numSamples * numChannels * 2);
    var view = new DataView(wav);
    var offset = 44;
    var channels = [];
    for (var c = 0; c < numChannels; c++) {
      channels.push(buffer.getChannelData(c));
    }
    for (var i = 0; i < buffer.length; i++) {
      for (var ch = 0; ch < numChannels; ch++) {
        var s = Math.max(-1, Math.min(1, channels[ch][i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        offset += 2;
      }
    }
    writeWavHeader(new DataView(wav), numChannels, sampleRate, numSamples);
    return wav;
  }

  function blobToArrayBuffer(blob) {
    return new Promise(function (resolve, reject) {
      var fr = new FileReader();
      fr.onload = function () { resolve(fr.result); };
      fr.onerror = reject;
      fr.readAsArrayBuffer(blob);
    });
  }

  function decodeAudioToWavBase64(blobOrFile) {
    var blob = blobOrFile instanceof File ? blobOrFile : blobOrFile;
    return blobToArrayBuffer(blob).then(function (arrayBuffer) {
      return new Promise(function (resolve, reject) {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        ctx.decodeAudioData(arrayBuffer.slice(0), function (audioBuffer) {
          var wav = audioBufferToWav(audioBuffer);
          resolve(arrayBufferToBase64(wav));
        }, function (err) {
          reject(new Error('Could not decode audio: ' + (err && err.message ? err.message : 'unknown')));
        });
      });
    });
  }

  // ----- API call -----
  function showError(msg) {
    if (resultsError && resultsErrorText) {
      resultsErrorText.textContent = msg;
      resultsError.hidden = false;
    }
    resultsPlaceholder.hidden = true;
    resultsContent.hidden = true;
  }

  function hideError() {
    if (resultsError) resultsError.hidden = true;
  }

  function showResults(data) {
    hideError();
    resultLanguage.textContent = data.language;
    resultType.textContent = data.type;
    resultType.className = 'result-value result-badge ' + (data.type.toLowerCase().indexOf('human') !== -1 ? 'human' : 'ai');
    resultConfidence.textContent = data.confidence;
    resultsPlaceholder.hidden = true;
    resultsContent.hidden = false;
  }

  function showPlaceholder() {
    hideError();
    resultsPlaceholder.hidden = false;
    resultsContent.hidden = true;
  }

  analyzeBtn.addEventListener('click', function () {
    if (!hasAudio()) return;

    var blob = currentAudioBlob || currentAudioFile;
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing…';
    hideError();

    decodeAudioToWavBase64(blob)
      .then(function (audioBase64) {
        return fetch(API_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': API_KEY
          },
          body: JSON.stringify({
            language: 'en',
            audio_format: 'wav',
            audio_base64: audioBase64
          })
        });
      })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (body) {
            throw new Error(body.detail || res.statusText || 'Request failed');
          }).catch(function () {
            throw new Error(res.statusText || 'Request failed');
          });
        }
        return res.json();
      })
      .then(function (data) {
        var type = data.prediction === 'HUMAN' ? 'Human' : 'AI-generated';
        var confidence = typeof data.confidence === 'number'
          ? Math.round(data.confidence * 100) + '%'
          : String(data.confidence);
        showResults({
          language: data.language || '—',
          type: type,
          confidence: confidence
        });
      })
      .catch(function (err) {
        var msg = err.message || 'Analysis failed.';
        if (msg === 'Failed to fetch' || msg.indexOf('NetworkError') !== -1 || msg.indexOf('Load failed') !== -1) {
          msg = 'Connection failed. Start the server (run run.bat or: python -m uvicorn main:app --reload from the ai-voice-detection- folder), then open this app at ' + SERVER_URL + ' in your browser.';
        }
        showError(msg);
      })
      .finally(function () {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze audio';
      });
  });
})();
