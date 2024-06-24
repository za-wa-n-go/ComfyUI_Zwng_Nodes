import os
import requests
import json
from server import PromptServer
from aiohttp import web
from googletrans import Translator, LANGUAGES

### =====  Translate Nodes [googletrans module]  ===== ###
translator = Translator()

# Manual translate prompts
@PromptServer.instance.routes.post("/wfs/translate_manual")
async def translate_manual(request):
    json_data = await request.json()
    print(f"Received JSON data: {json_data}")
    prompt = json_data.get("prompt", "")
    
    if "prompt" in json_data and "srcTrans" in json_data and "toTrans" in json_data:
        prompt = json_data.get("prompt")
        srcTrans = json_data.get("srcTrans")
        toTrans = json_data.get("toTrans")
      
        translate_text_prompt = translate(prompt, srcTrans, toTrans)
        print(f"Translated text: {translate_text_prompt}")
    
        return web.json_response({"translate_prompt": translate_text_prompt}) 
       
    return web.json_response({"translate_prompt": prompt})

def translate(prompt, srcTrans='auto', toTrans='en'):
    translate_text_prompt = ''
    if prompt and prompt.strip() != "":
        try:
            translate_text_prompt = translator.translate(prompt, src=srcTrans, dest=toTrans).text
            print(f"Translate function output: {translate_text_prompt}")
        except Exception as e:
            print(f"Translation error: {e}")
    return translate_text_prompt

class ZwngTranslateCLIPTextEncodeNode:
    
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "from_translate": (['auto']+list(LANGUAGES.keys()), {"default": "auto"}),
                "to_translate": (list(LANGUAGES.keys()), {"default": "en"}),
                "manual_translate": ([True, False], {"default": False}),
                "text": ("STRING", {"multiline": True, "placeholder": "Input prompt"}),
                "clip": ("CLIP",)
            }
        }

    RETURN_TYPES = ("CONDITIONING", "STRING",)
    FUNCTION = "translate_text"
    CATEGORY = "ZWNG/conditioning"

    def translate_text(self, **kwargs):
        from_translate = kwargs.get("from_translate")
        to_translate = kwargs.get("to_translate")
        manual_translate = kwargs.get("manual_translate", False)
        text = kwargs.get("text")
        clip = kwargs.get("clip")
              
        text_translated = translate(text, from_translate, to_translate) if not manual_translate else text
        tokens = clip.tokenize(text_translated)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return ([[cond, {"pooled_output": pooled}]], text_translated)

class ZwngSimpleGoogleTranslater(ZwngTranslateCLIPTextEncodeNode):

    @classmethod
    def INPUT_TYPES(self):
        return_types = super().INPUT_TYPES()
        del return_types["required"]["clip"]
        return return_types

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "translate_text"

    CATEGORY = "ZWNG/text"

    def translate_text(self, **kwargs):
        from_translate = kwargs.get("from_translate")
        to_translate = kwargs.get("to_translate")
        manual_translate = kwargs.get("manual_translate", False)
        text = kwargs.get("text")
              
        text_translated = translate(text, from_translate, to_translate) if not manual_translate else text
        return (text_translated,)
    
### =====  Translate Nodes [googletrans module] -> end ===== ###


NODE_CLASS_MAPPINGS = {
    'ZwngSimpleGoogleTranslater': ZwngSimpleGoogleTranslater,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'ZwngSimpleGoogleTranslater': 'Simple Google Translater',
}
