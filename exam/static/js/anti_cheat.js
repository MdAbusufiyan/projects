(function(){
  var cfg = window.EXAM_CONFIG.antiCheat;
  var examId = window.EXAM_CONFIG.examId;
  var blurStart = null;
  var blurTimer = null;

  function reportViolation(type, details){
    apiFetch('/exam/' + examId + '/api/violation', {
      method: 'POST',
      body: JSON.stringify({ type: type, details: details || '' })
    }).then(function(res){
      if (res.action === 'terminated' || res.action === 'auto_submit') {
        window.location.href = '/exam/' + examId + '/room';
      } else if (res.warnings) {
        var el = document.getElementById('warning-count');
        if (el) el.textContent = res.warnings;
      }
    }).catch(function(){});
  }
  window.reportViolation = reportViolation;

  if (cfg.disableCopy) {
    document.addEventListener('copy', function(e){ e.preventDefault(); reportViolation('copy'); });
  }
  if (cfg.disablePaste) {
    document.addEventListener('paste', function(e){ e.preventDefault(); reportViolation('paste'); });
  }
  if (cfg.disableRightClick) {
    document.addEventListener('contextmenu', function(e){ e.preventDefault(); reportViolation('right_click'); });
  }
  if (cfg.disableDragDrop) {
    document.addEventListener('dragstart', function(e){ e.preventDefault(); });
    document.addEventListener('drop', function(e){ e.preventDefault(); });
  }
  if (cfg.disableTextSelection) {
    document.body.style.userSelect = 'none';
    document.body.style.webkitUserSelect = 'none';
  }
  if (cfg.disablePrinting) {
    window.addEventListener('beforeprint', function(e){ reportViolation('print_attempt'); });
    document.addEventListener('keydown', function(e){
      if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) {
        e.preventDefault();
        reportViolation('print_attempt');
      }
    });
  }
  if (cfg.disableRefresh) {
    window.addEventListener('beforeunload', function(e){
      e.preventDefault();
      e.returnValue = '';
      return '';
    });
    document.addEventListener('keydown', function(e){
      if (e.key === 'F5' || ((e.ctrlKey || e.metaKey) && e.key === 'r')) {
        e.preventDefault();
        reportViolation('refresh_attempt');
      }
    });
  }

  if (cfg.detectTabSwitch) {
    document.addEventListener('visibilitychange', function(){
      if (document.hidden) {
        reportViolation('tab_switch', 'Tab hidden');
      }
    });
  }

  if (cfg.detectWindowBlur) {
    window.addEventListener('blur', function(){
      blurStart = Date.now();
      blurTimer = setTimeout(function(){
        reportViolation('blur', 'Exceeded max seconds outside window');
      }, cfg.maxSecondsOutside * 1000);
    });
    window.addEventListener('focus', function(){
      if (blurTimer) { clearTimeout(blurTimer); blurTimer = null; }
      if (blurStart) {
        var elapsed = (Date.now() - blurStart) / 1000;
        if (elapsed > 2) { reportViolation('blur', 'Window blurred for ' + Math.round(elapsed) + 's'); }
        blurStart = null;
      }
    });
  }

  if (cfg.requireFullscreen) {
    function requestFS(){
      var el = document.documentElement;
      var req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen;
      if (req) req.call(el).catch(function(){});
    }
    document.addEventListener('click', function once(){
      requestFS();
      document.removeEventListener('click', once);
    }, { once: true });

    if (cfg.detectFullscreenExit) {
      document.addEventListener('fullscreenchange', function(){
        if (!document.fullscreenElement) {
          reportViolation('fullscreen_exit');
        }
      });
    }
  }

  document.addEventListener('keydown', function(e){
    if (e.key === 'F12' ||
        ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C')) ||
        ((e.ctrlKey || e.metaKey) && (e.key === 'u' || e.key === 'U'))) {
      e.preventDefault();
      reportViolation('devtools_attempt');
    }
  });
})();
