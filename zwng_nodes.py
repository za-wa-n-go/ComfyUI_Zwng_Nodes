# import torch, os, sys, subprocess, random, math, hashlib, json, time, requests, re, tempfile, base64, subprocess
# import torch.nn as nn
# import torchvision.transforms as transforms
# import numpy as np
# from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageChops
# from PIL.PngImagePlugin import PngInfo
# from urllib.request import urlopen
# from io import BytesIO

# import comfy.samplers
# import comfy.sd
# import comfy.utils
# import importlib
# import nodes

# from nodes import MAX_RESOLUTION, SaveImage
# from comfy_extras.nodes_mask import ImageCompositeMasked
# from comfy.cli_args import args
# from comfy.utils import ProgressBar, common_upscale
# import model_management


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

class ZwngLoadImagePath:

    def __init__(self):
        self.input_dir = os.path.join(os.getcwd()+'/ComfyUI', "input")
        
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"image_path": ("STRING", {"default": '"./input/example.png"', "multiline": False}),}
                }

    CATEGORY = "ZWNG"

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"
    def load_image(self, image_path):
        image_path = re.sub(r'^"(.*)"$', r'\1', image_path)
            
        if image_path.startswith('http'):
            from io import BytesIO
            i = self.download_image(image_path)
        else:
            try:
                i = Image.open(image_path)
            except OSError:
                print(f'\033[34mWAS NS\033[0m Error: The image `{image_path.strip()}` specified doesn\'t exist!')
                i = Image.new(mode='RGB', size=(512,512), color=(0,0,0))
                
        image = i
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        
        if 'A' in i.getbands():
            mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
        return ( image, mask )

    def download_image(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            return img
        except requests.exceptions.HTTPError as errh:
            print(f"\033[34mWAS NS\033[0m Error: HTTP Error: ({url}): {errh}") 
        except requests.exceptions.ConnectionError as errc:
            print(f"\033[34mWAS NS\033[0m Error: Connection Error: ({url}): {errc}")  
        except requests.exceptions.Timeout as errt:
            print(f"\033[34mWAS NS\033[0m Error: Timeout Error: ({url}): {errt}")
        except requests.exceptions.RequestException as err:
            print(f"\033[34mWAS NS\033[0m Error: Request Exception: ({url}): {err}")
        
    @classmethod
    def IS_CHANGED(s, image_path):
        image_path = re.sub(r'^"(.*)"$', r'\1', image_path)

        if image_path.startswith('http'):
            return True
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()


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
    RETURN_NAMES = ("Photoshop Active Window", "Mask")
    FUNCTION = "PS_Execute"
    CATEGORY = "ZWNG"

    def PS_Execute(self, password, Server):
        Selection_To_Mask = True
        port = 49494
        
        try:
            from photoshop import PhotoshopConnection
        except:
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
                var e = app.activeDocument;
                var a = e.selection.bounds;
                var t = e.activeHistoryState;
                var i = e.artLayers.add();
                var s = new SolidColor();
                var r = e.artLayers.add();
                var l = new SolidColor();
                var c = new File("{self.MaskDir}");
                var n = new JPEGSaveOptions();
                s.rgb.hexValue = "000000";
                l.rgb.hexValue = "FFFFFF";
                e.activeLayer = r;
                e.selection.fill(l);
                e.activeLayer = i;
                e.selection.selectAll();
                e.selection.fill(s);
                n.quality = 1;
                e.saveAs(c, n, true);
                e.activeHistoryState = t;
            }} catch (y) {{
                File("{self.MaskDir}").remove();
                console.log("Error in mask creation: " + y.toString());
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
            self.loadImg(self.MaskDir)
            self.i = ImageOps.exif_transpose(self.i)
            self.mask = np.array(self.i.getchannel('B')).astype(np.float32) / 255.0
            self.mask = torch.from_numpy(self.mask)
        else:
            self.i = Image.new(mode='RGB', size=(1, 1), color=(0, 0, 0))
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


class ZwngPreviewImageAndMask(SaveImage):
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for x in range(5))
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mask_opacity": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }
    
    FUNCTION = "execute"
    CATEGORY = "ZWNG"

    def execute(self, mask_opacity, filename_prefix="ComfyUI", image=None, mask=None, prompt=None, extra_pnginfo=None):
        mask_color = (255, 0, 0) 
        
        if mask is not None and image is None:
            preview = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3)
        elif mask is None and image is not None:
            preview = image
        elif mask is not None and image is not None:
            mask_adjusted = mask * mask_opacity
            mask_image = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3).clone()

            mask_image[:, :, :, 0] = mask_color[0] / 255.0  # Red channel
            mask_image[:, :, :, 1] = mask_color[1] / 255.0  # Green channel
            mask_image[:, :, :, 2] = mask_color[2] / 255.0  # Blue channel
            
            preview, = ImageCompositeMasked.composite(self, image, mask_image, 0, 0, True, mask_adjusted)
            
        return(self.save_images(preview, filename_prefix, prompt, extra_pnginfo))


NODE_CLASS_MAPPING = {
    "ZwngPreviewImageAndMask": ZwngPreviewImageAndMask,
    "ZwngSimplePhotoshopConnector": ZwngSimplePsConnections,
    "ZwngLoadImagePath": ZwngLoadImagePath,
}
NODE_DISPLAY_NAME_MAPPING = {
    "ZwngPreviewImageAndMask": "Preview Image & Mask",
    "ZwngSimplePhotoshopConnector": "Simple Photoshop Connector",
    "ZwngLoadImagePath": "Load Image Path",
}