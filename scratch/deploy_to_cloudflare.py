import os, dotenv, httpx, zipfile, io

dotenv.load_dotenv()

account_id = "dfaa79724f2c8012bf5f62d495cee3d2"
api_token = os.getenv("CLOUDFLARE_API_TOKEN")

print("=== Cloudflare Pages Direct Deploy 가동 ===")

base_dir = os.path.dirname(os.path.abspath(__file__))
dist_dir = os.path.join(os.path.dirname(base_dir), "dist")

# dist 폴더 파일 zip 메모리 압축
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, dist_dir)
            zip_file.write(file_path, arcname)

zip_buffer.seek(0)

# Cloudflare Pages Direct Upload API
url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/auto-upload-video/deployments"
headers = {
    "Authorization": f"Bearer {api_token}"
}

files = {
    "file": ("dist.zip", zip_buffer, "application/zip")
}

try:
    res = httpx.post(url, headers=headers, files=files, timeout=30.0).json()
    print("Cloudflare Deploy Result:", res)
except Exception as e:
    print("Deploy Exception:", e)
