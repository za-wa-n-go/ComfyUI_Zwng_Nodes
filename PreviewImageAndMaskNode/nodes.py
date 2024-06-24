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
    CATEGORY = "WFSnodes/Image"

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

NODE_CLASS_MAPPINGS = {
    'ZwngPreviewImageAndMask': ZwngPreviewImageAndMask,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'ZwngPreviewImageAndMask': 'Preview Image & Mask',
}