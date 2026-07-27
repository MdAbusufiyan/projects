(function(){
  document.documentElement.classList.remove('js-checking');
  var banner = document.getElementById('js-disabled-banner');
  if (banner) banner.style.display = 'none';

  window.__jsAlive = true;

  function getCsrfToken(){
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }
  window.getCsrfToken = getCsrfToken;

  window.__jsHeartbeatFailures = 0;
})();
