import torch, os, sys, re, tempfile, folder_paths, random
import numpy as np
import comfy.samplers
import comfy.utils
import nodes

from PIL import Image, ImageOps
from io import BytesIO
from urllib.request import urlopen
from nodes import MAX_RESOLUTION, SaveImage
from comfy.utils import ProgressBar, common_upscale
from comfy_extras.nodes_mask import ImageCompositeMasked

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))
sys.path.append('../ComfyUI')

import nodes

class ZwngSimplePsConnections:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "password": ("STRING", {"default": "12341234"}),
                "Server": ("STRING", {"default": "127.0.0.1"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("Active Window", "Selection to Mask")
    FUNCTION = "PS_Execute"
    CATEGORY = "ZWNG"

    def PS_Execute(self, password, Server):
        Selection_To_Mask = True
        port = 49494
        
        try:
            from photoshop import PhotoshopConnection
        except ImportError:
            subprocess.run(["python", "-m", "pip", "uninstall", "photoshop"], check=True)
            subprocess.run(["python", "-m", "pip", "uninstall", "photoshop-connection"], check=True)
            subprocess.run(["python", "-m", "pip", "install", "photoshop-connection"], check=True)
        
        self.TmpDir = tempfile.gettempdir().replace("\\", "/")
        self.ImgDir = f"{self.TmpDir}/temp_image.jpg"
        self.MaskDir = f"{self.TmpDir}/temp_image_mask.jpg"
        
        ImgScript = f'''var saveFile = new File("{self.ImgDir}"); var jpegOptions = new JPEGSaveOptions(); jpegOptions.quality = 10; activeDocument.saveAs(saveFile, jpegOptions, true);'''
        
        Maskscript = f'''
        function main() {{
            try {{
                var doc = app.activeDocument;
                var hasSelection = true;
                try {{
                    var bounds = doc.selection.bounds; // Check if there is a selection
                }} catch (e) {{
                    hasSelection = false; // No selection present
                }}

                var t = doc.activeHistoryState;
                var layerMask = doc.artLayers.add();
                
                if (!hasSelection) {{
                    var s = new SolidColor();
                    doc.selection.selectAll();
                    s.rgb.hexValue = "000000";
                    doc.activeLayer = layerMask;
                    doc.selection.fill(s);
                }} else {{
                    var s = new SolidColor();
                    var r = doc.artLayers.add();
                    var l = new SolidColor();
                    s.rgb.hexValue = "000000";
                    l.rgb.hexValue = "FFFFFF";
                    doc.activeLayer = r;
                    doc.selection.fill(l);
                    doc.activeLayer = layerMask;
                    doc.selection.selectAll();
                    doc.selection.fill(s);
                }}

                var maskFile = new File("{self.MaskDir}");
                var saveOptions = new JPEGSaveOptions();
                saveOptions.quality = 1;
                doc.saveAs(maskFile, saveOptions, true);
                doc.activeHistoryState = t;

                if (!hasSelection) {{
                    doc.selection.deselect(); // Deselect if there was no initial selection
                }}

            }} catch (y) {{
                alert("Error in mask creation: " + y.toString());
                File("{self.MaskDir}").remove();
            }}
        }}
        app.activeDocument.suspendHistory("Mask Applied", "main()");
        '''

        with PhotoshopConnection(password=password, host=Server, port=port) as ps_conn:
            ps_conn.execute(ImgScript)
            if Selection_To_Mask:
                ps_conn.execute(Maskscript)

        self.SendImg(Selection_To_Mask)
        return (self.image, self.mask, self.width, self.height)

    def SendImg(self, Selection_To_Mask):
        self.loadImg(self.ImgDir)
        self.image = self.i.convert('RGB')
        self.image = np.array(self.image).astype(np.float32) / 255.0
        self.image = torch.from_numpy(self.image)[None,]
        self.width, self.height = self.i.size
        
        if Selection_To_Mask:
            if not os.path.exists(self.MaskDir):
                print("Mask file does not exist, creating a white mask.")
                self.mask = torch.ones((1, self.height, self.width), dtype=torch.float32)
            else:
                self.loadImg(self.MaskDir)
                self.i = ImageOps.exif_transpose(self.i)
                self.mask = np.array(self.i.getchannel('B')).astype(np.float32) / 255.0
                self.mask = torch.from_numpy(self.mask)

    def loadImg(self, path):
        try:
            self.i = Image.open(path)
            self.i.verify()
            self.i = Image.open(path)
        except Exception as e:
            print("Error loading image: ", e)
            self.i = Image.new(mode='RGB', size=(1, 1), color=(0, 0, 0))

    @classmethod
    def IS_CHANGED(cls, ImgDir, MaskDir):
        with open(ImgDir, "rb") as img_file:
            if os.path.exists(MaskDir):
                with open(MaskDir, "rb") as mask_file:
                    return base64.b64encode(mask_file.read()).decode('utf-8') + base64.b64encode(img_file.read()).decode('utf-8')
            else:
                return base64.b64encode(img_file.read()).decode('utf-8')

NODE_CLASS_MAPPINGS = {
    'ZwngSimplePhotoshopConnector': ZwngSimplePsConnections,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'ZwngSimplePhotoshopConnector': 'Simple Photoshop Connector',
}