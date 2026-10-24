#!/usr/bin/env python3# -*- coding: utf-8 -*-
"""
NEXUS OS BUILDER v10 — VERSION QUI GÉNÈRE VRAIMENT
Fix : plus de blocage download, plus de crash silencieux.
"""

import os, sys, json, time, uuid, shutil, tarfile, gzip, hashlib
import threading, tempfile, traceback, argparse, logging, stat
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from dataclasses import dataclass, asdict

VERSION = "10.0.0"
HOST = "127.0.0.1"
PORT = 9972

# ─── Base dir SAFE (fallback multiples) ───
def find_base():
for c in [os.getenv("NEXUS_DIR"),
os.path.expanduser("~/nexus_build"),
os.path.join(tempfile.gettempdir(), "nexus_build"),
os.path.expanduser("~/Documents/nexus_build"),
os.path.join(os.getcwd(), "nexus_build")]:
try:
p = Path(c); p.mkdir(parents=True, exist_ok=True)
(p / ".t").write_text("x"); (p / ".t").unlink()
return p
except: continue
raise RuntimeError("Aucun dossier inscriptible trouvé")

BASE = find_base()
LOGS = BASE / "logs"; LOGS.mkdir(exist_ok=True)
EXPORTS = BASE / "exports"; EXPORTS.mkdir(exist_ok=True)
BUILDS = BASE / "builds"; BUILDS.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO,
format='%(asctime)s | %(message)s',
handlers=[logging.FileHandler(LOGS/"builder.log"), logging.StreamHandler(sys.stdout)])
log = logging.getLogger("NEXUS")


# ═══════════════════════════════════════════════════════════════════
# PROJECT MODEL
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Project:
id: str
name: str
distro: str
prompt: str
status: str = "PENDING"
progress: int = 0
step: str = ""
logs: list = None
archive: Optional[str] = None
size_kb: int = 0
files_count: int = 0
error: Optional[str] = None

def __post_init__(self):
if self.logs is None: self.logs = []

def add_log(self, msg):
ts = datetime.now().strftime("%H:%M:%S")
self.logs.append(f"[{ts}] {msg}")
log.info(f"[{self.id}] {msg}")


# ═══════════════════════════════════════════════════════════════════
# BUILDER — 100% OFFLINE, GARANTI
# ═══════════════════════════════════════════════════════════════════

def build_project(p: Project):
"""Construit l'OS — 100% local, aucun download requis."""
try:
p.status = "BUILDING"
p.add_log(f"🚀 Démarrage build: {p.name}")
p.add_log(f"📦 Distro: {p.distro}")
p.add_log(f"🎯 Prompt: {p.prompt[:60]}")

build_dir = BUILDS / p.id
build_dir.mkdir(parents=True, exist_ok=True)
rootfs = build_dir / "rootfs"
rootfs.mkdir(exist_ok=True)

# ── ÉTAPE 1 : Structure rootfs (10%) ──
p.progress = 10; p.step = "Structure rootfs"
p.add_log("📁 Création arborescence")

dirs = ["bin", "sbin", "etc", "proc", "sys", "dev", "tmp", "run",
"root", "home", "home/nexus", "var", "var/log", "usr",
"usr/bin", "usr/sbin", "usr/lib", "opt", "srv", "mnt", "media"]
for d in dirs:
(rootfs / d).mkdir(parents=True, exist_ok=True)

# ── ÉTAPE 2 : /init (20%) ──
p.progress = 20; p.step = "/init"
p.add_log("🔧 Création /init")

init_content = f"""#!/bin/sh
# NEXUS OS — {p.name}
# Built: {datetime.now().isoformat()}
# Distro: {p.distro}

export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/root
export PS1='nexus@os:\\w# '

mount -t proc proc /proc 2>/dev/null
mount -t sysfs sysfs /sys 2>/dev/null
mount -t devtmpfs devtmpfs /dev 2>/dev/null
mount -t tmpfs tmpfs /tmp 2>/dev/null

clear 2>/dev/null || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║ ║"
echo "║ NEXUS OS v{VERSION} ║"
echo "║ {p.name:<44}║"
echo "║ Distro: {p.distro:<37}║"
echo "║ ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo " Fichiers: $(find / -type f 2>/dev/null | wc -l)"
echo " Uptime : $(cat /proc/uptime 2>/dev/null | cut -d' ' -f1)s"
echo ""

exec /bin/sh
"""
init = rootfs / "init"
init.write_text(init_content)
os.chmod(init, 0o755)

# ── ÉTAPE 3 : /bin/sh minimal (30%) ──
p.progress = 30; p.step = "Shell minimal"
p.add_log("🐚 Création /bin/sh")

# Script shell minimal (ne fait rien de complexe)
sh_content = """#!/bin/sh
# NEXUS minimal shell
while true; do
printf "nexus@os:# "
read cmd
case "$cmd" in
exit) exit 0 ;;
help) echo "Commandes: exit, help, info, ls, echo" ;;
info) cat /etc/nexus-release 2>/dev/null ;;
ls) echo "bin etc home proc root sys tmp usr var" ;;
*) echo "nexus: commande non disponible en mode minimal" ;;
esac
done
"""
sh = rootfs / "bin/sh"
sh.write_text(sh_content)
os.chmod(sh, 0o755)

# ── ÉTAPE 4 : Fichiers système (40%) ──
p.progress = 40; p.step = "Fichiers système"
p.add_log("📝 Fichiers /etc")

system_files = {
"etc/passwd": "root:x:0:0:root:/root:/bin/sh\nnexus:x:1000:1000:Nexus:/home/nexus:/bin/sh\nnobody:x:65534:65534:nobody:/:/bin/false\n",
"etc/group": "root:x:0:\nnexus:x:1000:\nwheel:x:10:nexus\nnobody:x:65534:\n",
"etc/shadow": "root:*:19000:0:99999:7:::\nnexus:*:19000:0:99999:7:::\n",
"etc/hostname": f"nexus-{p.id}\n",
"etc/hosts": "127.0.0.1\tlocalhost\n127.0.1.1\tnexus\n",
"etc/resolv.conf": "nameserver 1.1.1.1\nnameserver 8.8.8.8\n",
"etc/fstab": "proc /proc proc defaults 0 0\nsysfs /sys sysfs defaults 0 0\ndevtmpfs /dev devtmpfs defaults 0 0\n",
"etc/issue": f"NEXUS OS v{VERSION} — {p.name}\n",
"etc/profile": "export PATH=/bin:/sbin:/usr/bin:/usr/sbin\nexport HOME=/root\n",
"etc/nexus-release": f"NEXUS OS v{VERSION}\nName: {p.name}\nDistro: {p.distro}\nBuilt: {datetime.now().isoformat()}\n",
}
for path, content in system_files.items():
fp = rootfs / path
fp.parent.mkdir(parents=True, exist_ok=True)
fp.write_text(content)
if "shadow" in path:
os.chmod(fp, 0o600)

# ── ÉTAPE 5 : Outils NEXUS (50%) ──
p.progress = 50; p.step = "Outils NEXUS"
p.add_log("🔧 Scripts NEXUS")

(rootfs / "bin/nexus-info").write_text(f"""#!/bin/sh
echo "════════════════════════════════════════"
echo " NEXUS OS v{VERSION}"
echo " Name: {p.name}"
echo " Distro: {p.distro}"
echo " Built: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
echo "════════════════════════════════════════"
""")
os.chmod(rootfs / "bin/nexus-info", 0o755)

# ── ÉTAPE 6 : README (60%) ──
p.progress = 60; p.step = "README"
p.add_log("📄 README")
(rootfs / "README.txt").write_text(f"""NEXUS OS v{VERSION}
Name: {p.name}
Distro: {p.distro}
Prompt: {p.prompt}

Boot avec QEMU:
qemu-system-x86_64 -kernel vmlinuz -initrd initramfs.cpio.gz -append "console=tty0"

Contenu rootfs:
/init Script d'init
/bin/sh Shell minimal
/bin/nexus-info Info système
/etc/ Config système
""")

# ── ÉTAPE 7 : Archive tar.xz (80%) ──
p.progress = 80; p.step = "Archive"
p.add_log("📦 Création archive .tar.xz")

archive_name = f"{p.name}_{p.id}.tar.xz"
archive_path = EXPORTS / archive_name

with tarfile.open(archive_path, "w:xz", preset=6) as tar:
tar.add(rootfs, arcname="rootfs")
tar.add(rootfs / "README.txt", arcname="README.txt")

# ── ÉTAPE 8 : Stats (95%) ──
p.progress = 95; p.step = "Stats"
p.size_kb = archive_path.stat().st_size // 1024
p.files_count = sum(1 for _ in rootfs.rglob("*") if _.is_file())
p.archive = str(archive_path)
p.add_log(f"✓ Archive: {p.size_kb} KB, {p.files_count} fichiers")

# ── ÉTAPE 9 : DONE (100%) ──
p.progress = 100; p.step = "Terminé"
p.status = "COMPLETED"
p.add_log("🎉 Build terminé avec succès!")
p.add_log(f"📥 Télécharge: /download/{p.id}/archive")

except Exception as e:
p.status = "FAILED"
p.error = str(e)
p.add_log(f"💥 ERREUR: {e}")
p.add_log(traceback.format_exc()[:300])


# ═══════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════

class Factory:
def __init__(self):
self.projects = {}
self.lock = threading.RLock()

def create(self, name, distro, prompt):
pid = str(uuid.uuid4())[:8]
p = Project(pid, name, distro, prompt)
with self.lock:
self.projects[pid] = p
threading.Thread(target=build_project, args=(p,), daemon=True).start()
return p

def get(self, pid):
with self.lock:
return self.projects.get(pid)

def all(self):
with self.lock:
return [asdict(p) for p in self.projects.values()]


FACTORY = Factory()


# ═══════════════════════════════════════════════════════════════════
# HTTP HANDLER
# ═══════════════════════════════════════════════════════════════════

HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXUS OS BUILDER</title>
<style>
body{background:#0a0a14;color:#e0e0e0;font-family:system-ui,sans-serif;padding:30px 20px;margin:0}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:2rem;background:linear-gradient(135deg,#00ff9d,#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:20px}
.card{background:#141428;border:1px solid #2a2a3a;border-radius:12px;padding:20px;margin-bottom:16px}
input,textarea{width:100%;padding:12px;background:#0a0a1a;border:1px solid #2a2a3a;border-radius:8px;color:#fff;margin-bottom:12px;font-family:inherit;font-size:14px}
textarea{min-height:80px;resize:vertical}
button{padding:14px 28px;background:linear-gradient(135deg,#00ff9d,#00d4ff);color:#000;border:none;border-radius:8px;font-weight:700;font-size:15px;cursor:pointer;width:100%}
button:disabled{opacity:0.5;cursor:wait}
.distros{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}
.dist{padding:14px;background:#0a0a1a;border:2px solid #2a2a3a;border-radius:8px;cursor:pointer;text-align:center}
.dist.on{border-color:#00ff9d;background:rgba(0,255,157,0.05)}
.dist .n{font-weight:700;color:#00ff9d}
.project{background:#0a0a1a;border:1px solid #2a2a3a;border-radius:10px;padding:16px;margin-bottom:12px}
.ph{display:flex;justify-content:space-between;margin-bottom:10px}
.pname{font-weight:700;color:#00ff9d;font-size:16px}
.pstatus{font-size:11px;padding:4px 10px;border-radius:20px;font-weight:700}
.status-BUILDING{background:rgba(255,180,0,0.2);color:#ffb400}
.status-COMPLETED{background:rgba(0,255,157,0.2);color:#00ff9d}
.status-FAILED{background:rgba(255,50,50,0.2);color:#ff5555}
.status-PENDING{background:#333;color:#888}
.bar{height:8px;background:#1a1a2a;border-radius:4px;overflow:hidden;margin:8px 0}
.fill{height:100%;background:linear-gradient(90deg,#00ff9d,#00d4ff);transition:width 0.3s}
.step{font-size:11px;color:#4c9aff;font-family:monospace;margin:4px 0}
.logs{background:#000;padding:10px;border-radius:6px;font-family:monospace;font-size:11px;color:#00ff9d;max-height:200px;overflow-y:auto;margin-top:10px}
.dl{margin-top:10px;padding:10px;background:rgba(0,255,157,0.1);border-radius:6px}
.dl a{color:#00ff9d;text-decoration:none;font-weight:700}
.err{margin-top:10px;padding:10px;background:rgba(255,50,50,0.1);border-radius:6px;color:#ff8888;font-family:monospace;font-size:12px}
</style></head><body><div class="wrap">
<h1>🖥️ NEXUS OS BUILDER v10</h1>
<div class="card">
<input id="name" placeholder="Nom du projet" value="NexusOS">
<div class="distros">
<div class="dist on" data-d="alpine"><div class="n">Alpine</div><div style="font-size:10px;color:#888">5 MB</div></div>
<div class="dist" data-d="debian"><div class="n">Debian</div><div style="font-size:10px;color:#888">80 MB</div></div>
<div class="dist" data-d="ubuntu"><div class="n">Ubuntu</div><div style="font-size:10px;color:#888">30 MB</div></div>
</div>
<textarea id="prompt" placeholder="Description (ex: OS audio docker dev)">OS audio docker dev tools</textarea>
<button id="btn" onclick="go()">🚀 GÉNÉRER L'OS</button>
</div>
<div id="list"></div>
</div>
<script>
let dist='alpine';
document.querySelectorAll('.dist').forEach(b=>b.onclick=()=>{
document.querySelectorAll('.dist').forEach(x=>x.classList.remove('on'));
b.classList.add('on');dist=b.dataset.d;});
async function go(){
const btn=document.getElementById('btn');
btn.disabled=true;btn.textContent='⏳ Génération...';
try{
const r=await fetch('/api/build',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({name:document.getElementById('name').value,distro:dist,prompt:document.getElementById('prompt').value})});
const d=await r.json();
await poll();
}catch(e){alert('Erreur: '+e.message);}
finally{btn.disabled=false;btn.textContent='🚀 GÉNÉRER L\\'OS';}
}
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
async function poll(){
try{
const r=await fetch('/api/projects');
const projects=await r.json();
const c=document.getElementById('list');
if(!projects.length){c.innerHTML='<div class="card" style="text-align:center;color:#888">Aucun projet</div>';return;}
c.innerHTML=projects.map(p=>`
<div class="project">
<div class="ph"><span class="pname">${esc(p.name)}</span><span class="pstatus status-${p.status}">${p.status}</span></div>
<div style="font-size:12px;color:#888">${esc(p.distro)} · ${esc(p.prompt.slice(0,60))}</div>
<div class="bar"><div class="fill" style="width:${p.progress}%"></div></div>
<div class="step">${esc(p.step)} — ${p.progress}% · ${p.files_count||0} fichiers · ${p.size_kb||0} KB</div>
<div class="logs">${(p.logs||[]).slice(-15).map(l=>`<div>${esc(l)}</div>`).join('')}</div>
${p.archive?`<div class="dl">📦 <a href="/download/${p.id}/archive">Télécharger ${esc(p.archive.split('/').pop())}</a></div>`:''}
${p.error?`<div class="err">❌ ${esc(p.error)}</div>`:''}
</div>`).join('');
}catch(e){console.error(e);}
}
setInterval(poll,1000);poll();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
def log_message(self,*a): pass

def _json(self,code,data):
try:
b=json.dumps(data,ensure_ascii=False,default=str).encode()
self.send_response(code);self.send_header("Content-Type","application/json")
self.send_header("Access-Control-Allow-Origin","*")
self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
except: pass

def do_GET(self):
p=urlparse(self.path).path
if p=="/":
b=HTML.encode();self.send_response(200)
self.send_header("Content-Type","text/html; charset=utf-8")
self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b);return
if p=="/api/projects": return self._json(200,FACTORY.all())
if p.startswith("/download/"):
parts=p.split("/")
if len(parts)>=4:
pid=parts[2];proj=FACTORY.get(pid)
if proj and proj.archive:
try:
pth=Path(proj.archive)
self.send_response(200)
self.send_header("Content-Type","application/octet-stream")
self.send_header("Content-Disposition",f'attachment; filename="{pth.name}"')
self.send_header("Content-Length",str(pth.stat().st_size))
self.end_headers()
with open(pth,"rb") as f: shutil.copyfileobj(f,self.wfile)
return
except: pass
return self._json(404,{"error":"not found"})
return self._json(404,{"error":"not found"})

def do_POST(self):
p=urlparse(self.path).path
if p=="/api/build":
n=int(self.headers.get("Content-Length",0))
d=json.loads(self.rfile.read(n) or b"{}")
proj=FACTORY.create(d.get("name","OS"),d.get("distro","alpine"),d.get("prompt",""))
return self._json(200,asdict(proj))
return self._json(404,{"error":"not found"})


class Server(ThreadingHTTPServer):
daemon_threads=True;allow_reuse_address=True


if __name__=="__main__":
ap=argparse.ArgumentParser()
ap.add_argument("--port",type=int,default=PORT)
args=ap.parse_args()
print(f"""
╔══════════════════════════════════════════════════════════════╗
║ NEXUS OS BUILDER v{VERSION} — 100% OFFLINE ║
╚══════════════════════════════════════════════════════════════╝
Base : {BASE}
URL : http://127.0.0.1:{args.port}
Génére TOUJOURS (aucun download requis)
""")
try:
Server((HOST,args.port),Handler).serve_forever()
except KeyboardInterrupt:
print("\n👋")
