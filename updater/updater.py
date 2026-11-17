import bpy
import os
import urllib.request
import ssl
import json
import zipfile
import shutil
import tempfile
from datetime import datetime

GITHUB_REPO = "explainervid-glitch/zeuslab-addon"
RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ASSET_PREFIX = "ZeusLab-v"  # Release asset name: ZeusLab-v<version>.zip
USER_AGENT = "ZeusLab-Blender-Addon"  # GitHub API rejects requests without a User-Agent


def _ssl_context():
    """Verified SSL context. Uses certifi when the system store is missing."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _open(url, accept=None):
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, context=_ssl_context(), timeout=30)


def _parse_version(tag):
    """'v1.10.0' -> (1, 10, 0)"""
    return tuple(int(part) for part in tag.lstrip("vV").split("."))


class ZeusLabUpdater:
    """Class untuk mengelola update addon ZeusLab (sumber: GitHub Releases)"""

    def __init__(self):
        self.addon_name = "ZeusLab"
        self.addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.temp_dir = os.path.join(tempfile.gettempdir(), "zeuslab_update")

    def check_for_updates(self):
        """Cek release terbaru di GitHub. Returns (has_update, version, download_url, changelog)"""
        try:
            with _open(RELEASE_API_URL, accept="application/vnd.github+json") as response:
                data = json.loads(response.read())

            latest_version = _parse_version(data["tag_name"])
            asset = next((a for a in data.get("assets", [])
                          if a["name"].startswith(ASSET_PREFIX) and a["name"].endswith(".zip")), None)
            if asset is None:
                print(f"ZeusLab updater: release {data['tag_name']} has no {ASSET_PREFIX}*.zip asset")
                return False, None, "", ""

            from .. import bl_info
            current_version = tuple(bl_info["version"])

            if latest_version > current_version:
                return True, latest_version, asset["browser_download_url"], data.get("body") or ""
            return False, current_version, "", ""

        except Exception as e:
            print(f"Error saat memeriksa update: {str(e)}")
            return False, None, "", ""

    def is_dev_install(self):
        """True bila addon dijalankan dari repo git / symlink: update akan menghapus repo"""
        addon_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Path as Blender sees it
        return (os.path.exists(os.path.join(self.addon_dir, ".git")) or
                os.path.islink(addon_path) or
                os.path.realpath(addon_path) != os.path.abspath(addon_path))

    def download_and_install_update(self, download_url):
        """Download dan install update addon"""
        if self.is_dev_install():
            return False, ("Development install (git repo or symlink) detected. "
                           "Update with git pull instead, so the repo is not overwritten.")
        try:
            # Mulai dari direktori temp yang bersih
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir)

            # Path file zip untuk download
            zip_path = os.path.join(self.temp_dir, "zeuslab_update.zip")

            # Download file zip (GitHub redirect ke storage, urlopen mengikuti redirect)
            with _open(download_url, accept="application/octet-stream") as response:
                with open(zip_path, 'wb') as out_file:
                    out_file.write(response.read())
            
            # Ekstrak file zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Dapatkan nama folder di dalam zip
                zip_folder_name = zip_ref.namelist()[0].split('/')[0]
                
                # Ekstrak semua file
                zip_ref.extractall(self.temp_dir)
            
            # Backup folder addon lama
            backup_dir = os.path.join(tempfile.gettempdir(), f"zeuslab_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            shutil.copytree(self.addon_dir, backup_dir)
            
            # Hapus folder addon lama (kecuali __pycache__ dan user settings)
            exclude_dirs = ['__pycache__']
            for item in os.listdir(self.addon_dir):
                item_path = os.path.join(self.addon_dir, item)
                if os.path.isdir(item_path):
                    if item not in exclude_dirs:
                        shutil.rmtree(item_path)
                elif os.path.isfile(item_path) and item != 'user_settings.json':
                    os.remove(item_path)
            
            # Salin file baru
            src_dir = os.path.join(self.temp_dir, zip_folder_name)
            for item in os.listdir(src_dir):
                s = os.path.join(src_dir, item)
                d = os.path.join(self.addon_dir, item)
                if os.path.isdir(s):
                    if not os.path.exists(d):
                        os.makedirs(d)
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            
            # Bersihkan direktori temp
            shutil.rmtree(self.temp_dir)
            
            return True, "Update berhasil diinstal. Silakan restart Blender untuk menerapkan perubahan."
            
        except Exception as e:
            print(f"Error saat menginstal update: {str(e)}")
            return False, f"Gagal menginstal update: {str(e)}"
            
# Singleton instance
updater = ZeusLabUpdater()