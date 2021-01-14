# Copyright (c) 2021 -- Elie Michel
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# The Software is provided “as is”, without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose and noninfringement. In no event shall
# the authors or copyright holders be liable for any claim, damages or other
# liability, whether in an action of contract, tort or otherwise, arising from,
# out of or in connection with the software or the use or other dealings in the
# Software.

bl_info = {
    "name": "Lily Image From URL",
    "author": "Élie Michel",
    "version": (1, 0, 0),
    "blender": (2, 90, 0),
    "location": "UV/Image Editor > From Url",
    "description": "Import an image from the URL currently in the clipboard",
    "warning": "",
    "doc_url": "https://github.com/eliemichel/LilyImageFromURL",
    "category": "Import",
}

import bpy
from bpy.types import Operator, IMAGE_MT_image, IMAGE_MT_editor_menus
from bpy.props import BoolProperty, StringProperty

import requests
from urllib.parse import urlparse
from mimetypes import guess_extension
from os.path import join
from tempfile import gettempdir
import shutil

class CannotDownload(Exception):
    pass

def make_filename(url, response):
    filename = urlparse(url).path.split('/')[-1]
    mime = response.headers['content-type']
    ext = guess_extension(mime)
    if not filename.endswith(ext):
        filename += ext
    return filename

def download_image_direct(url):
    headers = {"User-Agent":"Mozilla/5.0"}  # fake user agent
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise CannotDownload(f"Http request returned status {r.status_code}")
    
    filename = make_filename(url, r)
    raw_data = r.content
    
    # Not working, we have to go through an actual file :/
    # So we use download_image_via_file instead for now
    img = bpy.data.images.new(filename, width=1, height=1)
    img.source = 'FILE'
    img.filepath = filename
    img.pack(data=raw_data)
    img.reload()
    return img

def download_image_via_file(url):
    headers = {"User-Agent":"Mozilla/5.0"}  # fake user agent
    r = requests.get(url, stream=True, headers=headers)
    if r.status_code != 200:
        raise CannotDownload(f"Http request returned status {r.status_code}")
    
    tmp_dir = gettempdir()
    filename = make_filename(url, r)
    filepath = join(tmp_dir, filename)
    
    with open(filepath, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)
        
    img = bpy.data.images.load(filepath)
    img.name = filename
    return img

download_image = download_image_via_file

class ImageFromUrl(Operator):
    bl_idname = "lily.image_from_url"
    bl_label = "New Image from URL"
    
    url: StringProperty(
        name = "URL",
        description = "URL of the image to import, ignored if use_clipboard is turned on",
        default = "",
    )
    
    use_clipboard: BoolProperty(
        name = "Import from Clipboard",
        description = "Get the URL of the image to import from the clipboard rather than using the url property",
        default = True
    )
    
    def execute(self, context):
        if self.use_clipboard:
            url = context.window_manager.clipboard
        else:
            url = self.url
            
        try:
            img = download_image(url)
        except CannotDownload as e:
            self.report({'ERROR'}, f"Cannot download image from url '{url}': {e.message}")
            return {'CANCELLED'}
        
        area = context.area
        if area.type == 'IMAGE_EDITOR' :
                context.area.spaces.active.image = img
            
        return {'FINISHED'}

def draw_menu(self, context):
    layout = self.layout
    layout.operator(ImageFromUrl.bl_idname)
    
def draw_menu_short(self, context):
    layout = self.layout
    layout.operator(ImageFromUrl.bl_idname, text="From URL")

classes = (
    ImageFromUrl,
)
register_cls, unregister_cls = bpy.utils.register_classes_factory(classes)

def register():
    register_cls()
    IMAGE_MT_image.append(draw_menu)
    IMAGE_MT_editor_menus.append(draw_menu_short)

def unregister():
    IMAGE_MT_image.remove(draw_menu)
    IMAGE_MT_editor_menus.append(draw_menu_short)
    unregister_cls()

if __name__ == "__main__":
    register()
