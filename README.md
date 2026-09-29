# Projects Workspace

This repository contains two small web applications:

- Exam: a Flask-based online examination platform for professors and candidates.
- Mindmap: a simple browser-based mind map frontend served by a small Flask app.

The Mindmap app can also expose a masked route to the Exam app so the Exam service can be reached without showing the raw internal address in the browser.

## Requirements

- Python 3.10 or newer
- A working terminal
- Internet access for installing Python packages

## Quick start

From the repository root:

```bash
cd /mnt/data/project
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements/requirements.txt
```

If you are using Windows PowerShell, use:

```powershell
cd C:\path\to\project
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements\requirements.txt
```

## Run the Exam app

```bash
cd exam
python app.py
```

The Exam app will start on:

- http://127.0.0.1:8520

The first run creates the local database file automatically.

## Run the Mindmap app

In a second terminal:

```bash
cd mindmap
python server.py
```

The Mindmap app will start on:

- http://127.0.0.1:8765

Open that address in the browser. The page includes a link to the Exam app through the masked route.

## Optional: point the masked route to a different Exam host

If the Exam app is not running on the same machine or is hosted elsewhere, set the target before starting the Mindmap server:

```bash
export EXAM_TARGET=http://your-exam-host:8520
cd mindmap
python server.py
```

On Windows PowerShell:

```powershell
$env:EXAM_TARGET="http://your-exam-host:8520"
cd mindmap
python server.py
```

## Project layout

```text
exam/          # Flask exam platform
mindmap/       # Mindmap frontend and simple Flask server
requirements/  # Shared Python dependencies
```

## Notes

- The Exam app uses SQLite locally by default.
- The Mindmap app is intended for local use and demonstration.
- If you need to deploy this to a server, the two apps should usually be run behind a proper reverse proxy such as Nginx.

## SEO and Search Indexing

SEO updates made on 2026-09-29:

- The Mindmap server publishes `https://chooogle.com/robots.txt` and generates `https://chooogle.com/sitemap.xml` from its public-page list.
- The sitemap includes the homepage, resume, public project pages, and SDS/MSDS PDF. The exam app is not included.
- Public HTML responses receive canonical URLs and Open Graph URL metadata for `https://chooogle.com`.
- Portfolio pages include page-specific descriptions and social preview metadata. The homepage includes Person structured data for Abu Sufiyan.
- The Exam app and its proxied routes send `X-Robots-Tag: noindex, nofollow` so operational exam pages are not listed in search results. `robots.txt` allows crawlers to access these responses and read that directive.

The Mindmap server defaults its canonical and sitemap base to `https://chooogle.com`. If the public hostname changes, set `PUBLIC_SITE_URL` before starting the server. For example, in Windows PowerShell:

```powershell
$env:PUBLIC_SITE_URL="https://chooogle.com"
cd mindmap
python server.py
```

After deploying, check that `/robots.txt` and `/sitemap.xml` load on the public domain, then submit `https://chooogle.com/sitemap.xml` in Google Search Console and Bing Webmaster Tools. Search engines decide when and whether to index pages; these settings make the public pages discoverable but do not guarantee rankings.
