function apiFetch(url, options){
  options = options || {};
  options.headers = options.headers || {};
  options.headers['Content-Type'] = 'application/json';
  options.headers['X-CSRFToken'] = window.getCsrfToken ? window.getCsrfToken() : '';
  options.credentials = 'same-origin';
  return fetch(url, options).then(function(res){
    if (!res.ok) {
      return res.json().catch(function(){ return {}; }).then(function(body){
        throw { status: res.status, body: body };
      });
    }
    return res.json();
  });
}

function formatTime(totalSeconds){
  totalSeconds = Math.max(0, Math.floor(totalSeconds));
  var h = Math.floor(totalSeconds / 3600);
  var m = Math.floor((totalSeconds % 3600) / 60);
  var s = totalSeconds % 60;
  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  return (h > 0 ? h + ':' : '') + pad(m) + ':' + pad(s);
}

function debounce(fn, wait){
  var t;
  return function(){
    var args = arguments, ctx = this;
    clearTimeout(t);
    t = setTimeout(function(){ fn.apply(ctx, args); }, wait);
  };
}
