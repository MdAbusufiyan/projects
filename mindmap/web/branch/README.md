Move your existing Branch app file(s) here — specifically `Mindmap.html` — unchanged.

Nothing about Branch itself needs to change. Only its location moves, from
`web/Mindmap.html` to `web/branch/Mindmap.html`, so the site root (`/`) is free
for the new Choogle landing page. `server.py` has been updated to serve Branch
from `/branch/` accordingly (see server.py comments).
