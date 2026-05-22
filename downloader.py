import sys, os, json, tempfile, subprocess, urllib.request, zipfile, webbrowser

# Suppress OpenGL warnings
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"

from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap
import yt_dlp

# ============================================================
# AUTO-DOWNLOAD FFMPEG IF MISSING
# ============================================================
def get_ffmpeg_path():
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", "ffmpeg.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                     "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
                     "ffmpeg-8.1.1-full_build", "bin", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p

    try:
        result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True, shell=True)
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip().split("\n")[0].strip()
            if os.path.exists(path):
                return path
    except:
        pass

    return download_ffmpeg()

def download_ffmpeg():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_exe = os.path.join(script_dir, "ffmpeg.exe")

    if os.path.exists(ffmpeg_exe):
        return ffmpeg_exe

    print("FFmpeg not found. Downloading automatically...")
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = os.path.join(script_dir, "ffmpeg.zip")

    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as z:
            for f in z.namelist():
                if f.endswith("/bin/ffmpeg.exe"):
                    with z.open(f) as src, open(ffmpeg_exe, "wb") as dst:
                        dst.write(src.read())
                    break
        os.remove(zip_path)
        print("FFmpeg downloaded successfully!")
        return ffmpeg_exe
    except Exception as e:
        print(f"Failed to download FFmpeg: {e}")
        return None

FFMPEG_PATH = get_ffmpeg_path()
if FFMPEG_PATH:
    os.environ["PATH"] = os.path.dirname(FFMPEG_PATH) + os.pathsep + os.environ.get("PATH", "")
    print(f"FFmpeg found at: {FFMPEG_PATH}")
else:
    print("WARNING: FFmpeg could not be found or downloaded.")

# ============================================================
# WORKER: Fetch video info in background
# ============================================================
class WorkerThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best[ext=mp4]/best',
            }
            if FFMPEG_PATH:
                ydl_opts['ffmpeg_location'] = FFMPEG_PATH

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                formats = []
                for f in info['formats']:
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'resolution': f.get('resolution') or 'audio only',
                        'vcodec': f.get('vcodec', 'none'),
                        'acodec': f.get('acodec', 'none'),
                        'filesize': f.get('filesize'),
                        'format_note': f.get('format_note', ''),
                        'abr': f.get('abr', ''),
                    })
                result = {
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'formats': formats,
                    'url': self.url,
                    'webpage_url': info.get('webpage_url')
                }
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

# ============================================================
# DOWNLOAD WORKER
# ============================================================
class DownloadThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, opts):
        super().__init__()
        self.url = url
        self.opts = opts

    def run(self):
        try:
            with yt_dlp.YoutubeDL(self.opts) as ydl:
                ydl.download([self.url])
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YTDownloader - Private YouTube Downloader")
        self.setGeometry(100, 100, 900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # ---- URL Input Row ----
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here...")
        self.url_input.setMinimumHeight(35)
        self.load_btn = QPushButton("🔍 Load Video")
        self.load_btn.setMinimumHeight(35)
        self.load_btn.clicked.connect(self.load_video)
        url_layout.addWidget(self.url_input, 4)
        url_layout.addWidget(self.load_btn, 1)
        layout.addLayout(url_layout)

        # ---- Thumbnail + Preview Button ----
        preview_layout = QHBoxLayout()
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 180)
        self.thumbnail_label.setStyleSheet("background-color: #222; border-radius: 8px;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("🎬")
        self.thumbnail_label.setScaledContents(True)
        preview_layout.addWidget(self.thumbnail_label)

        preview_info_layout = QVBoxLayout()
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 15px; font-weight: bold; padding: 5px;")
        self.info_label.setWordWrap(True)
        preview_info_layout.addWidget(self.info_label)

        self.preview_btn = QPushButton("▶ Preview in Browser")
        self.preview_btn.setMinimumHeight(35)
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self.preview_in_browser)
        preview_info_layout.addWidget(self.preview_btn)
        preview_info_layout.addStretch()
        preview_layout.addLayout(preview_info_layout)
        layout.addLayout(preview_layout)

        # ---- Download Options ----
        self.download_group = QGroupBox("📥 Download Options")
        self.download_group.setVisible(False)
        dl_layout = QVBoxLayout()
        self.download_group.setLayout(dl_layout)

        fmt_qual_layout = QHBoxLayout()
        fmt_qual_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4 (video)", "webm (video)", "mp3 (audio)", "m4a (audio)"])
        self.format_combo.currentIndexChanged.connect(self.populate_qualities)
        fmt_qual_layout.addWidget(self.format_combo)
        fmt_qual_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        fmt_qual_layout.addWidget(self.quality_combo)
        dl_layout.addLayout(fmt_qual_layout)

        self.download_btn = QPushButton("⬇ Start Download")
        self.download_btn.setMinimumHeight(35)
        self.download_btn.clicked.connect(self.start_download)
        dl_layout.addWidget(self.download_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        dl_layout.addWidget(self.progress_bar)

        layout.addWidget(self.download_group)
        layout.addStretch()

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready - Paste a YouTube URL and click 'Load Video'")

        self.video_data = None
        self.worker = None
        self.preview_url = None

    def load_video(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please paste a YouTube URL.")
            return
        self.load_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.status_bar.showMessage("Fetching video info...")
        self.worker = WorkerThread(url)
        self.worker.finished.connect(self.on_info_loaded)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_info_loaded(self, data):
        self.video_data = data
        self.load_btn.setEnabled(True)
        self.status_bar.showMessage(f"✅ Loaded: {data['title']}")
        self.info_label.setText(f"🎬 {data['title']}")

        # Load thumbnail
        if data.get('thumbnail'):
            try:
                import urllib.request as ur
                thumb_data = ur.urlopen(data['thumbnail']).read()
                pixmap = QPixmap()
                pixmap.loadFromData(thumb_data)
                self.thumbnail_label.setPixmap(pixmap.scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                self.thumbnail_label.setText("🎬")

        # Find preview URL (prefer a combined stream that plays in browser)
        self.preview_url = None
        for f in data['formats']:
            if f['ext'] == 'mp4' and f['vcodec'] != 'none' and f['acodec'] != 'none':
                if f['resolution'] in ['640x360', '854x480', '1280x720']:
                    self.preview_url = self.get_stream_url(data['url'], f['format_id'])
                    break
        if not self.preview_url:
            for f in data['formats']:
                if f['vcodec'] != 'none' and f['acodec'] != 'none':
                    self.preview_url = self.get_stream_url(data['url'], f['format_id'])
                    break

        self.preview_btn.setEnabled(self.preview_url is not None)

        self.populate_qualities()
        self.download_group.setVisible(True)

    def preview_in_browser(self):
        if self.preview_url:
            # Create a simple HTML file and open in browser
            html_path = os.path.join(tempfile.gettempdir(), "yt_preview.html")
            html = f'''<!DOCTYPE html>
<html><head><title>YTDownloader Preview</title></head>
<body style="margin:0; background:#000; display:flex; justify-content:center; align-items:center; height:100vh;">
<video width="100%" height="auto" controls autoplay style="max-width:100%; max-height:100vh;">
    <source src="{self.preview_url}" type="video/mp4">
    Your browser cannot play this video.
</video>
</body></html>'''
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            webbrowser.open("file://" + html_path)
        else:
            QMessageBox.information(self, "No Preview", "No playable preview URL found. You can still download the video.")

    def get_stream_url(self, video_url, format_id):
        try:
            ydl_opts = {'quiet': True, 'format': format_id}
            if FFMPEG_PATH:
                ydl_opts['ffmpeg_location'] = FFMPEG_PATH
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                for f in info['formats']:
                    if f['format_id'] == format_id:
                        return f.get('url')
        except:
            pass
        return None

    def populate_qualities(self):
        self.quality_combo.clear()
        fmt = self.format_combo.currentText().split()[0]
        if not self.video_data:
            return

        qualities = set()

        if fmt in ['mp3', 'm4a']:
            for f in self.video_data['formats']:
                if f['vcodec'] == 'none' and f['ext'] == 'm4a':
                    abr = f.get('abr')
                    if abr:
                        qualities.add(f"{abr} kbps")
                    else:
                        note = f.get('format_note', '')
                        if note:
                            qualities.add(note)
            if not qualities:
                qualities.add("best audio")
            quality_list = sorted(
                qualities,
                key=lambda x: int(x.split()[0]) if x.split()[0].isdigit() else 0,
                reverse=True
            )
        else:
            for f in self.video_data['formats']:
                if f['vcodec'] != 'none' and f['ext'] == fmt:
                    res = f.get('resolution') or ''
                    if 'x' in res:
                        try:
                            height = res.split('x')[1]
                            qualities.add(f"{height}p")
                        except:
                            pass
                    elif f.get('format_note'):
                        note = f['format_note']
                        if 'p' in note:
                            qualities.add(note)
            quality_list = sorted(
                qualities,
                key=lambda x: int(x.replace('p', '')) if x.replace('p', '').isdigit() else 0,
                reverse=True
            )

        if quality_list:
            self.quality_combo.addItems(quality_list)
        else:
            self.quality_combo.addItem("best")

    def start_download(self):
        if not self.video_data:
            return
        format_choice = self.format_combo.currentText().split()[0]
        quality = self.quality_combo.currentText()

        if format_choice in ['mp3', 'm4a']:
            fmt_str = 'bestaudio/best'
        else:
            if quality == 'best' or not quality:
                fmt_str = f'bestvideo[ext={format_choice}]+bestaudio[ext=m4a]/best[ext={format_choice}]/best'
            else:
                height = quality.replace('p', '').split()[0]
                fmt_str = f'bestvideo[height<={height}][ext={format_choice}]+bestaudio[ext=m4a]/best[height<={height}][ext={format_choice}]/best'

        default_ext = format_choice
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Video", self.video_data['title'] + f".{default_ext}",
            f"*.{default_ext}"
        )
        if not save_path:
            return

        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("⬇ Downloading...")

        ydl_opts = {
            'format': fmt_str,
            'outtmpl': save_path,
            'progress_hooks': [self.progress_hook],
            'postprocessors': [],
            'merge_output_format': format_choice if format_choice in ['mp4', 'webm'] else None,
        }
        if FFMPEG_PATH:
            ydl_opts['ffmpeg_location'] = FFMPEG_PATH

        if format_choice == 'mp3':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_choice == 'm4a':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }]

        self.dl_thread = DownloadThread(self.video_data['url'], ydl_opts)
        self.dl_thread.finished.connect(self.download_finished)
        self.dl_thread.error.connect(self.download_error)
        self.dl_thread.start()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                p = d['_percent_str'].replace('%', '').strip()
                self.progress_bar.setValue(int(float(p)))
            except:
                pass
        elif d['status'] == 'finished':
            self.progress_bar.setValue(100)
            self.status_bar.showMessage("Processing file...")

    def download_finished(self):
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("✅ Download complete!")
        QMessageBox.information(self, "Success", "Video downloaded successfully!")

    def download_error(self, msg):
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("❌ Download failed")
        QMessageBox.critical(self, "Error", f"Download failed:\n{msg}")

    def on_error(self, msg):
        self.load_btn.setEnabled(True)
        self.status_bar.showMessage("❌ Error loading video")
        QMessageBox.critical(self, "Error", f"Could not load video:\n{msg}")

# ============================================================
# RUN APP
# ============================================================
if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    app = QApplication(sys.argv)

    # Set a clean stylesheet
    app.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; }
        QLabel { color: #e0e0e0; }
        QGroupBox { color: #e0e0e0; font-weight: bold; border: 1px solid #444; border-radius: 8px; margin-top: 10px; padding-top: 15px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QLineEdit { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #444; border-radius: 5px; padding: 8px; }
        QPushButton { background-color: #e63946; color: white; border: none; border-radius: 5px; padding: 8px 16px; font-weight: bold; }
        QPushButton:hover { background-color: #ff4d5a; }
        QPushButton:disabled { background-color: #555; color: #999; }
        QComboBox { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #444; border-radius: 5px; padding: 5px; }
        QProgressBar { background-color: #2d2d2d; border: 1px solid #444; border-radius: 5px; text-align: center; color: white; }
        QProgressBar::chunk { background-color: #e63946; border-radius: 5px; }
        QStatusBar { color: #999; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())