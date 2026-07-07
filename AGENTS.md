# Code with Etan!

A static, client-side educational website teaching Python basics (Home, Loops, Variables, Type casts) with embedded video tutorials. Pure HTML/CSS — no JavaScript, no backend, no database, no package manager, and no build/test/lint tooling.

## Cursor Cloud specific instructions

- This is a static site. There is nothing to install, build, lint, or test — there are no manifests, lockfiles, or config files.
- The home page is `CWE.html` (not `index.html`), so serving the folder and opening `/` will not show the site; open `/CWE.html` explicitly.
- To run it in development, serve the repo root with any static server and open the home page, e.g. `python3 -m http.server 8000` then visit `http://localhost:8000/CWE.html`.
- Some filenames and asset paths contain spaces (e.g. `Type cast.html`, `Videos/For loops - Made with Clipchamp.mp4`); URL-encode spaces as `%20` when requesting them.
- Assets are referenced with mixed-case folder names (`Photos/`, `Videos/`, `Logo/`, `Font/`); a case-sensitive Linux server requires the paths to match exactly as on disk.
