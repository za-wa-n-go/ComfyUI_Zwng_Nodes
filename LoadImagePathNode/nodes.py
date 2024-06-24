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
                i = Image.open(image_path).convert("RGBA")
            except OSError:
                print(f'\033[34mWAS NS\033[0m Error: The image {image_path.strip()} specified doesn\'t exist!')
                i = Image.new(mode='RGBA', size=(512, 512), color=(0, 0, 0, 0))
                
        image_np = np.array(i).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np)[None,]

        out_images = [img[:,:,:3] for img in image_tensor]
        out_alphas = [img[:,:,3] if img.shape[2] > 3 else torch.ones_like(img[:,:,0]) for img in image_tensor]
        result_image = torch.stack(out_images)
        result_mask = torch.stack(out_alphas)  # ここではアルファチャンネルをそのまま使用
        
        return (result_image, result_mask)

    def download_image(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGBA")
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

NODE_CLASS_MAPPINGS = {
    'ZwngLoadImagePath': ZwngLoadImagePath,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'ZwngLoadImagePath': 'Load Image Path',
}
