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

class ZwngLoadImagePathOrURL:
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
            i = self.load_image_from_url(image_path)
        else:
            try:
                i = Image.open(image_path).convert("RGBA")
            except OSError:
                print(f'\033[34mWAS NS\033[0m Error: The image {image_path.strip()} specified doesn\'t exist!')
                i = Image.new(mode='RGBA', size=(512, 512), color=(0, 0, 0, 0))
                
        image_np = np.array(i).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np)[None,]
        out_images = [img[:,:,:3] for img in image_tensor]
        out_alphas = [img[:,:,3] if img.shape[2] > 3 else None for img in image_tensor]
        result_image = torch.stack(out_images)
        result_mask = torch.stack(out_alphas) if out_alphas[0] is not None else None
        
        return (result_image, result_mask)

    def load_image_from_url(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")
        except requests.exceptions.RequestException as err:
            print(f"\033[34mWAS NS\033[0m Error: Failed to load image from URL: ({url}): {err}")
            return Image.new(mode='RGBA', size=(512, 512), color=(0, 0, 0, 0))
        
    @classmethod
    def IS_CHANGED(s, image_path):
        image_path = re.sub(r'^"(.*)"$', r'\1', image_path)
        if image_path.startswith('http'):
            return True
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

NODE_CLASS_MAPPINGS = {
    'ZwngLoadImagePathOrURL': ZwngLoadImagePathOrURL,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'ZwngLoadImagePathOrURL': 'Load Image Path or URL',
}
