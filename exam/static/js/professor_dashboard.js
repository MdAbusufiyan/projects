document.addEventListener('DOMContentLoaded', function(){

  var addBtn = document.getElementById('add-question-btn');
  if (addBtn) {
    addBtn.addEventListener('click', function(){
      var examId = addBtn.getAttribute('data-exam');
      var payload = new FormData();
      payload.append('question_text', document.getElementById('q_text').value);
      payload.append('option_a', document.getElementById('q_a').value);
      payload.append('option_b', document.getElementById('q_b').value);
      payload.append('option_c', document.getElementById('q_c').value);
      payload.append('option_d', document.getElementById('q_d').value);
      payload.append('correct_option', document.getElementById('q_correct').value);
      payload.append('marks', document.getElementById('q_marks').value);

      fetch('/professor/exams/' + examId + '/questions/add', {
        method: 'POST',
        headers: { 'X-CSRFToken': window.getCsrfToken() },
        body: payload,
        credentials: 'same-origin'
      }).then(function(res){ return res.json(); })
        .then(function(data){
          if (data.ok) { window.location.reload(); }
        });
    });
  }

  document.querySelectorAll('.delete-question').forEach(function(btn){
    btn.addEventListener('click', function(){
      if (!confirm('Delete this question?')) return;
      var examId = btn.getAttribute('data-exam');
      var qid = btn.getAttribute('data-qid');
      fetch('/professor/exams/' + examId + '/questions/' + qid + '/delete', {
        method: 'POST',
        headers: { 'X-CSRFToken': window.getCsrfToken() },
        credentials: 'same-origin'
      }).then(function(res){ return res.json(); })
        .then(function(data){ if (data.ok) window.location.reload(); });
    });
  });

  var addRowBtn = document.getElementById('add-candidate-row');
  if (addRowBtn) {
    addRowBtn.addEventListener('click', function(){
      var wrap = document.getElementById('manual-candidates');
      var row = document.createElement('div');
      row.className = 'form-row';
      row.innerHTML = '<div class="form-group"><input name="names[]" placeholder="Name"></div>' +
                       '<div class="form-group"><input name="emails[]" placeholder="Email" type="email"></div>';
      wrap.appendChild(row);
    });
  }
});
