import os
import sys
import subprocess
import shutil
from pathlib import Path
from src.type_speech.config import config

# Build configuration
APP_NAME = "TypeSpeech"
BUILD_DIR = f"build/{APP_NAME}"


def clean_build_dirs():
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    # Clean new build structure
    if os.path.exists('build'):
        shutil.rmtree('build')


def copy_files():
    """Copy config, credentials, and assets to dist"""
    dist_dir = Path(BUILD_DIR)
    if not dist_dir.exists():
        return
    
    # Copy config files
    config_dir = dist_dir / 'config'
    config_dir.mkdir(exist_ok=True)
    for file in ['default.yaml', 'user.yaml']:
        src = Path('config') / file
        if src.exists():
            shutil.copy2(src, config_dir)
    
    # Create credentials directory (empty)
    cred_dir = dist_dir / 'credentials'
    cred_dir.mkdir(exist_ok=True)
    # Don't copy credential files for security
    
    # Copy assets
    assets_dir = dist_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)
    for file in Path('assets').iterdir():
        if file.is_file() and file.suffix.lower() in ['.ico', '.png']:
            shutil.copy2(file, assets_dir)
    

if __name__ == '__main__':
    clean_build_dirs()
    assets_dir = Path('assets').absolute()
    
    cmd = [
        'pyinstaller', '--onefile', '--windowed', f'--name={APP_NAME}',
        f'--distpath={BUILD_DIR}',
        '--workpath=build/work',
        '--specpath=build',
        f'--icon={assets_dir}/icon.ico',
        f'--add-data={assets_dir}/icon.ico;assets',
        '--hidden-import=pystray._util_win32',
        'app/tray_app.py'
    ]
    
    subprocess.run(cmd, check=True)
    
    # Remove spec file if exists
    spec_file = Path(f'build/{APP_NAME}.spec')
    if spec_file.exists():
        spec_file.unlink()
    
    copy_files()
    
    # Show results
    if os.path.exists(BUILD_DIR):
        for file in os.listdir(BUILD_DIR):
            if file.endswith('.exe'):
                size = os.path.getsize(os.path.join(BUILD_DIR, file)) / (1024 * 1024)
                print(f"{file} ({size:.1f} MB)")