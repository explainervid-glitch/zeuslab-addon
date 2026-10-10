import bpy
import os
import urllib.request
import ssl
import json
import zipfile
import shutil
import tempfile
from datetime import datetime

class ZeusLabUpdater:
    """Class untuk mengelola update addon ZeusLab"""
    
    def __init__(self):
        self.addon_name = "ZeusDev_Tools"
        self.addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.temp_dir = os.path.join(tempfile.gettempdir(), "zeuslab_update")
        
        # URL untuk file version.json di Google Drive
        # Buat file direct link dari Google Drive dengan format berikut
        self.version_url = "https://drive.google.com/uc?export=download&id=1kqlRz0pLqQmdXgImEXXcfh-7cbagi8SP"
        
    def check_for_updates(self):
        """Memeriksa apakah update tersedia"""
        try:
            # Bypass SSL verification untuk menghindari error
            context = ssl._create_unverified_context()
            
            # Download file version.json
            response = urllib.request.urlopen(self.version_url, context=context)
            data = json.loads(response.read())
            
            # Dapatkan versi saat ini dari bl_info
            from .. import bl_info
            current_version = bl_info["version"]
            
            # Bandingkan versi
            latest_version = tuple(data["version"])
            download_url = data["download_url"]
            
            if latest_version > current_version:
                return True, latest_version, download_url, data.get("changelog", "")
            else:
                return False, current_version, "", ""
                
        except Exception as e:
            print(f"Error saat memeriksa update: {str(e)}")
            return False, None, "", ""
            
    def download_and_install_update(self, download_url):
        """Download dan install update addon"""
        try:
            # Buat direktori temp jika belum ada
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
            
            # Path file zip untuk download
            zip_path = os.path.join(self.temp_dir, "zeuslab_update.zip")
            
            # Download file zip
            context = ssl._create_unverified_context()
            
            # Gunakan urlopen sebagai pengganti urlretrieve untuk dukungan context SSL
            with urllib.request.urlopen(download_url, context=context) as response:
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