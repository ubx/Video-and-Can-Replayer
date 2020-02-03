import os
from os.path import join

from kivy import kivy_data_dir
from kivy.tools.packaging import pyinstaller_hooks as hooks

block_cipher = None
kivy_deps_all = hooks.get_deps_all()
kivy_factory_modules = hooks.get_factory_modules()

datas = []

# list of modules to exclude from analysis
excludes = ['Tkinter', '_tkinter', 'twisted', 'pygments']

# list of hiddenimports
hiddenimports = kivy_deps_all['hiddenimports'] + kivy_factory_modules

# binary data

# assets
kivy_assets_toc = Tree(kivy_data_dir, prefix=join('kivy_install', 'data'))
source_assets_toc = []
assets_toc = [kivy_assets_toc, source_assets_toc]


a = Analysis(['VideoAndCanPlayer2.py'],
             pathex=['.'],
             binaries=None,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          name='VideoAndCanPlayer2',
          exclude_binaries=True,
          debug=False,
          strip=False,
          upx=True,
          console=False)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='VideoAndCanPlayer2')