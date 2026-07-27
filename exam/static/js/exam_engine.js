(function(){
  var cfg = window.EXAM_CONFIG;
  var examId = cfg.examId;
  var currentIndex = 0;
  var remainingSeconds = cfg.durationSeconds;
  var totalQuestions = cfg.totalQuestions;
  var timerEl = document.getElementById('exam-timer');
  var heartbeatFailCount = 0;
  var MAX_HEARTBEAT_FAILS = 3;

  var blocks = document.querySelectorAll('.question-block');
  var palette = document.getElementById('q-palette');

  function buildPalette(){
    palette.innerHTML = '';
    blocks.forEach(function(b, idx){
      var dot = document.createElement('div');
      dot.className = 'q-dot' + (idx === 0 ? ' current' : '');
      dot.textContent = idx + 1;
      dot.dataset.index = idx;
      var selected = b.querySelector('input[type=radio]:checked');
      if (selected) dot.classList.add('answered');
      dot.addEventListener('click', function(){ goToQuestion(idx); });
      palette.appendChild(dot);
    });
  }

  function goToQuestion(idx){
    if (idx < 0 || idx >= blocks.length) return;
    blocks.forEach(function(b, i){ b.style.display = (i === idx) ? 'block' : 'none'; });
    currentIndex = idx;
    document.querySelectorAll('.q-dot').forEach(function(d, i){
      d.classList.toggle('current', i === idx);
    });
    document.getElementById('btn-submit').style.display = (idx === blocks.length - 1) ? 'inline-block' : 'none';
    apiFetch('/exam/' + examId + '/api/navigate', {
      method: 'POST', body: JSON.stringify({ index: idx })
    }).catch(function(){});
  }

  blocks.forEach(function(block){
    block.querySelectorAll('.option-item').forEach(function(opt){
      opt.addEventListener('click', function(){
        var value = opt.dataset.value;
        var radio = block.querySelector('input[value="' + value + '"]');
        if (radio) radio.checked = true;
        block.querySelectorAll('.option-item').forEach(function(o){ o.classList.remove('selected'); });
        opt.classList.add('selected');

        var qid = block.dataset.qid;
        apiFetch('/exam/' + examId + '/api/answer', {
          method: 'POST', body: JSON.stringify({ question_id: qid, selected: value })
        }).then(function(){
          var idx = parseInt(block.dataset.qindex, 10);
          var dot = palette.querySelector('.q-dot[data-index="' + idx + '"]');
          if (dot) dot.classList.add('answered');
        }).catch(function(){});
      });
    });
  });

  document.getElementById('btn-prev').addEventListener('click', function(){ goToQuestion(currentIndex - 1); });
  document.getElementById('btn-next').addEventListener('click', function(){ goToQuestion(currentIndex + 1); });
  document.getElementById('btn-review').addEventListener('click', function(){ goToQuestion(0); });

  document.getElementById('btn-submit').addEventListener('click', function(){
    if (!confirm('Are you sure you want to submit the exam? This cannot be undone.')) return;
    finalSubmit();
  });

  function finalSubmit(){
    apiFetch('/exam/' + examId + '/api/submit', { method: 'POST', body: JSON.stringify({}) })
      .then(function(res){
        window.location.href = '/exam/' + examId + '/room';
      }).catch(function(){
        window.location.href = '/exam/' + examId + '/room';
      });
  }

  function updateTimerDisplay(){
    timerEl.textContent = formatTime(remainingSeconds);
    timerEl.className = 'exam-timer';
    if (remainingSeconds <= 60) timerEl.classList.add('danger');
    else if (remainingSeconds <= 300) timerEl.classList.add('warning');
  }

  var timerInterval = setInterval(function(){
    remainingSeconds -= 1;
    if (remainingSeconds <= 0) {
      remainingSeconds = 0;
      updateTimerDisplay();
      clearInterval(timerInterval);
      finalSubmit();
      return;
    }
    updateTimerDisplay();
  }, 1000);

  var heartbeatInterval = setInterval(function(){
    apiFetch('/exam/' + examId + '/api/heartbeat', {
      method: 'POST', body: JSON.stringify({ remaining_seconds: remainingSeconds })
    }).then(function(res){
      heartbeatFailCount = 0;
      if (res.time_up) {
        clearInterval(timerInterval);
        clearInterval(heartbeatInterval);
        window.location.href = '/exam/' + examId + '/room';
      }
    }).catch(function(){
      heartbeatFailCount += 1;
      if (heartbeatFailCount >= MAX_HEARTBEAT_FAILS) {
        window.reportViolation && window.reportViolation('js_disabled', 'Heartbeat failed repeatedly');
      }
    });
  }, 15000);

  // JS integrity self-check: periodically verify our own script tags are intact
  var integrityCheckInterval = setInterval(function(){
    if (!window.__jsAlive || typeof apiFetch !== 'function') {
      window.location.href = '/exam/' + examId + '/room';
    }
  }, 5000);

  buildPalette();
  updateTimerDisplay();
  window.addEventListener('beforeunload', function(){
    clearInterval(timerInterval);
    clearInterval(heartbeatInterval);
    clearInterval(integrityCheckInterval);
  });
})();
