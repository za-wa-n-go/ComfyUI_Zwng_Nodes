import os
import importlib.util
import subprocess
import sys
import shutil
import __main__
import pkgutil
import re
import threading

python = sys.executable

# Define directories for user extension files
extension_folder = os.path.dirname(os.path.realpath(__file__))

# ComfyUI folders web
folder_web = os.path.join(os.path.dirname(os.path.realpath(__main__.__file__)), "web")
folder_comfyui_web_extensions = os.path.join(folder_web, "extensions")

folder__web_lib = os.path.join(folder_web, 'lib')

# Debug mode toggle
DEBUG = False

# Logging function for debugging
def log(*text):
    if DEBUG:
        print(''.join(map(str, text)))

# Function to display subprocess output
def information(datas):
    for info in datas:
        if DEBUG:
            print(info, end="")

# Function to install modules using pip
def module_install(commands, cwd='.'):
    result = subprocess.Popen(commands, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    out = threading.Thread(target=information, args=(result.stdout,))
    err = threading.Thread(target=information, args=(result.stderr,))
    out.start()
    err.start()
    out.join()
    err.join()
    return result.wait()

# Check and install required modules for nodes
def checkModules(nodeElement):
    file_requir = os.path.join(extension_folder, nodeElement, 'requirements.txt')
    if os.path.exists(file_requir):
        log("  -> File 'requirements.txt' found!")
        module_install([sys.executable, '-s', '-m', 'pip', 'install', '-r', file_requir])
        return True
    return False

def printInfo(text):
    print(text)

def installNodes():
    log(f"\n-------> ZWNG Node Installing [DEBUG] <-------")
    # Remove files in lib directory 
    libfiles = ['fabric.js']
    for file in libfiles:
        filePath = os.path.join(folder__web_lib, file)
        if os.path.exists(filePath):
            os.remove(filePath)

    for nodeElement in os.listdir(extension_folder):
        if not nodeElement.startswith('__') and nodeElement.endswith('Node') and os.path.isdir(os.path.join(extension_folder, nodeElement)):
            node_installed_flag_path = os.path.join(extension_folder, nodeElement, '.installed')

            # Check if node is already installed
            if os.path.exists(node_installed_flag_path):
                log(f"* Node <{nodeElement}> is already installed, skipping installation...")
            else:
                log(f"* Node <{nodeElement}> is found, installing...")

                # Check and install required modules
                if checkModules(nodeElement):
                    # Mark node as installed
                    with open(node_installed_flag_path, 'w') as f:
                        f.write('installed')

# Mount web directory
WEB_DIRECTORY = os.path.join(extension_folder, 'SimpleGoogleTranslaterNode', 'js')

# Install nodes
installNodes()


# List of node modules to import
node_modules = [
    'LoadImagePathNode',
    'PreviewImageAndMaskNode',
    'SimplePhotoshopConnectorNode',
    'SimpleGoogleTranslaterNode'
]

# Initialize empty dictionaries for mappings
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Import and merge node mappings

log("--- ComfyUI ZWNG CustomNodes ---")
for module in node_modules:
    try:
        module_path = os.path.join(extension_folder, module)
        if os.path.exists(module_path):
            log(f"Node -> {module} [Loading]")  # Always print important messages
            mod = importlib.import_module(f'.{module}.nodes', package=__name__)
            NODE_CLASS_MAPPINGS.update(mod.NODE_CLASS_MAPPINGS)
            NODE_DISPLAY_NAME_MAPPINGS.update(mod.NODE_DISPLAY_NAME_MAPPINGS)
        else:
            print(f"Module path {module_path} does not exist.")  # Always print important messages
    except ImportError as e:
        print(f"Error importing {module}: {e}")  # Always print important messages
    except AttributeError as e:
        print(f"Error accessing NODE_CLASS_MAPPINGS or NODE_DISPLAY_NAME_MAPPINGS in {module}: {e}")  # Always print important messages

log("-------------------------------")

# Filter out the node mappings that are not in NODE_DISPLAY_NAME_MAPPINGS
filtered_node_class_mappings = {key: value for key, value in NODE_CLASS_MAPPINGS.items() if key in NODE_DISPLAY_NAME_MAPPINGS}

# Replace NODE_CLASS_MAPPINGS with the filtered version
NODE_CLASS_MAPPINGS = filtered_node_class_mappings


# Specify what is available for import from this module
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
