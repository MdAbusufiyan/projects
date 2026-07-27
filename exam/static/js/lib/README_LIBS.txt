Place the following third-party library files in this folder:

1. pdf.min.js        -> https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.js
2. pdf.worker.min.js  -> https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.js
3. chart.min.js       -> https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js

Download these once and host them locally (recommended for offline/low-bandwidth
ThinkPad + Cloudflare Tunnel deployments so the app does not depend on external CDNs
during an exam). Example:

  cd exam_platform/static/js/lib
  curl -O https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.js
  curl -O https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.js
  curl -O https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js

Socket.IO client is loaded from CDN in monitor.html (cdn.socket.io) — replace with a
local copy the same way if you need fully offline operation.
