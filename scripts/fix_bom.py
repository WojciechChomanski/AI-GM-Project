import os
import glob

def remove_bom(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    with open(file_path, 'wb') as f:
        f.write(content)

json_files = glob.glob('H:\\Code\\AI_GM_Project\\rules\\**\\*.json', recursive=True)
for file in json_files:
    remove_bom(file)
    print(f"Processed {file}")