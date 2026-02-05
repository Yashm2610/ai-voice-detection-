(function () {
  'use strict';

  // ----- DOM refs -----
  const recordBtn = document.getElementById('recordBtn');
  const recordingStatus = document.getElementById('recordingStatus');
  const fileInput = document.getElementById('fileInput');
  const dropZone = document.getElementById('dropZone');
  const selectedFile = document.getElementById('selectedFile');
  const fileName = document.getElementById('fileName');
  const clearFile = document.getElementById('clearFile');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const resultsPlaceholder = document.getElementById('resultsPlaceholder');
  const resultsContent = document.getElementById('resultsContent');
  const resultLanguage = document.getElementById('resultLanguage');
  const resultType = document.getElementById('resultType');
  const resultConfidence = document.getElementById('resultConfidence');

  // ----- State -----
  let mediaRecorder = null;
  let recordedChunks = [];
  let currentAudioBlob = null;
  let currentAudioFile = null;
  let stream = null;

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

  // Optional: hold to speak (touch/mouse)
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

  // ----- Analyze button -----
  function hasAudio() {
    return currentAudioBlob != null || currentAudioFile != null;
  }

  function updateAnalyzeButton() {
    analyzeBtn.disabled = !hasAudio();
  }

  // ----- Mock analysis (replace with your backend call) -----
  function mockAnalyze() {
    var languages = ['English', 'Spanish', 'French', 'German', 'Hindi', 'Mandarin', 'Arabic', 'Portuguese', 'Japanese'];
    var isHuman = Math.random() > 0.5;
    return {
      language: languages[Math.floor(Math.random() * languages.length)],
      type: isHuman ? 'Human' : 'AI-generated',
      confidence: (85 + Math.floor(Math.random() * 14)) + '%'
    };
  }

  function showResults(data) {
    resultLanguage.textContent = data.language;
    resultType.textContent = data.type;
    resultType.className = 'result-value result-badge ' + (data.type.toLowerCase().indexOf('human') !== -1 ? 'human' : 'ai');
    resultConfidence.textContent = data.confidence;
    resultsPlaceholder.hidden = true;
    resultsContent.hidden = false;
  }

  function showPlaceholder() {
    resultsPlaceholder.hidden = false;
    resultsContent.hidden = true;
  }

  analyzeBtn.addEventListener('click', function () {
    if (!hasAudio()) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing…';

    // Simulate API delay; replace with real fetch to your backend
    setTimeout(function () {
      var result = mockAnalyze();
      showResults(result);
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = 'Analyze audio';
    }, 1200);
  });

})();
