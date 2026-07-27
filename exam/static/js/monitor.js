document.addEventListener('DOMContentLoaded', function(){
  var socket = io({ transports: ['websocket', 'polling'] });

  socket.on('connect', function(){
    socket.emit('join_monitor', { exam_id: window.EXAM_ID });
  });

  function updateStats(){
    var rows = document.querySelectorAll('#monitor-table tbody tr');
    var inProgress = 0, submitted = 0, flagged = 0;
    rows.forEach(function(row){
      var status = row.querySelector('.col-status').textContent.trim();
      if (status === 'in_progress') inProgress++;
      if (status === 'submitted') submitted++;
      var warnings = parseInt(row.querySelector('.col-warnings').textContent, 10) || 0;
      if (warnings > 0) flagged++;
    });
    document.getElementById('stat-progress').textContent = inProgress;
    document.getElementById('stat-submitted').textContent = submitted;
    document.getElementById('stat-flagged').textContent = flagged;
  }

  socket.on('candidate_update', function(data){
    var row = document.querySelector('tr[data-candidate-id="' + data.candidate_id + '"]');
    if (!row) return;

    if (data.field === 'status') {
      row.querySelector('.col-status').textContent = data.value;
      row.className = 'status-' + data.value;
      if (data.score !== undefined && data.score !== null) {
        row.querySelector('.col-score').textContent = data.score;
      }
    } else if (data.field === 'current_question') {
      row.querySelector('.col-current-q').textContent = data.value;
    } else if (data.field === 'violation') {
      row.querySelector('.col-warnings').textContent = data.warnings;
      row.querySelector('.col-tabswitch').textContent = data.tab_switch_count;
      row.querySelector('.col-blur').textContent = data.blur_count;
      row.querySelector('.col-fsexit').textContent = data.fullscreen_exit_count;
      if (data.status) {
        row.querySelector('.col-status').textContent = data.status;
        row.className = 'status-' + data.status;
      }
    }
    updateStats();
  });

  updateStats();
  setInterval(updateStats, 5000);
});
