import os
import random
import subprocess
import urllib.request
import json
import re

AUDIO_DRIVE_FOLDER_ID = os.environ.get("AUDIO_FOLDER_ID")
IMAGES_DRIVE_FOLDER_ID = os.environ.get("IMAGES_FOLDER_ID")

def get_drive_files_via_api(folder_id):
    # Google Drive Public API ကို အသုံးပြု၍ ဖိုင်စာရင်းများကို တိကျစွာ ရယူခြင်း
    url = f"https://www.googleapis.com/drive/v3/files?q='{folder_id}'+in+parents&key=AIzaSyA..." # Public folder list query
    # API Key မလိုဘဲ Shared Drive/Folder များကို Alternative JSON Endpoint ဖြင့် တိုက်ရိုက်ဆွဲထုတ်ခြင်း
    alt_url = f"https://drive.google.com/drive/u/0/folders/{folder_id}"
    req = urllib.request.Request(alt_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    files = []
    try:
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
            
        # Google Drive ၏ internal JSON data (WIZ structure) ထဲမှ တကယ့် file ID နှင့် name များကို ရှာဖွေခြင်း
        # ဤ Pattern သည် .wav, .mp3 နှင့် ပုံဖိုင်နာမည်များကို တိကျစွာ ဖမ်းယူပေးပါသည်
        matches = re.findall(r'\["([a-zA-Z0-9_-]{25,})",\s*"([^"]+\.(?:wav|mp3|m4a|aac|ogg|flac|png|jpg|jpeg))"\s*,', html_content, re.IGNORECASE)
        
        seen_ids = set()
        for file_id, name in matches:
            if file_id not in seen_ids and file_id != folder_id:
                seen_ids.add(file_id)
                files.append({"id": file_id, "name": name})
                
        # အကယ်၍ အထက်ပါ Pattern ဖြင့် မမိပါက အထွေထွေ ဖိုင်နာမည်များကိုပါ ရှာဖွေမည့် fallback pattern
        if not files:
            general_matches = re.findall(r'\["([a-zA-Z0-9_-]{25,})",\s*"([^"]+)"', html_content)
            for file_id, name in general_matches:
                if file_id not in seen_ids and file_id != folder_id:
                    if not any(x in name.lower() for x in ["google", "http", "drive", "usercontent", "clients", "script", ".js", ".css"]):
                        seen_ids.add(file_id)
                        files.append({"id": file_id, "name": name})
                        
        return files
    except Exception as e:
        print(f"Drive ဖိုင်များကို ဖတ်ရှုရာတွင် အမှားအယွင်းရှိသည်: {e}")
        return []

def download_file(file_id, output_path):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    urllib.request.install_opener(opener)
    try:
        response = opener.open(url)
        content = response.read()
        if b"download_warning" in content or b"Virus scan warning" in content:
            match = re.search(r'confirm=([0-9A-Za-z_]+)', content.decode('utf-8', errors='ignore'))
            if match:
                confirm_token = match.group(1)
                confirmed_url = f"{url}&confirm={confirm_token}"
                response = opener.open(confirmed_url)
                content = response.read()
                
        with open(output_path, "wb") as f:
            f.write(content)
        print(f"ဒေါင်းလုဒ်လုပ်ပြီးပါပြီ: {output_path}")
    except Exception as e:
        print(f"ဒေါင်းလုဒ်ဆွဲ၍ မရပါ ({output_path}): {e}")

def main():
    print("ဗီဒီယို ဖန်တီးခြင်း လုပ်ငန်းစဉ် စတင်ပါပြီ...")

    os.makedirs("downloads", exist_ok=True)
    
    print("Google Drive ၏ audio ဖိုဒါကို စစ်ဆေးနေပါပြီ...")
    audio_files = get_drive_files_via_api(AUDIO_DRIVE_FOLDER_ID)
    print(f"တွေ့ရှိရသော အသံဖိုင်များ: {audio_files}")
    
    target_audio_id = None
    target_audio_name = "audio.wav"
    
    for f in audio_files:
        name_lower = f["name"].lower()
        if name_lower.endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac')):
            target_audio_id = f["id"]
            if name_lower.endswith('.mp3'):
                target_audio_name = "audio.mp3"
            else:
                target_audio_name = "audio.wav"
            print(f"အသုံးပြုမည့် အသံဖိုင်: {f['name']}")
            break
            
    # အကယ်၍ extension တိုက်ရိုက်မတွေ့ပါက ပထမဆုံး တွေ့ရှိသောဖိုင်ကို ယူမည်
    if not target_audio_id and audio_files:
        target_audio_id = audio_files[0]["id"]
        print(f"သတ်မှတ်လိုက်သော အသံဖိုင်: {audio_files[0]['name']}")

    if not target_audio_id:
        print("Error: Google Drive ၏ audio ဖိုဒါထဲတွင် အသံဖိုင် မတွေ့ရှိရပါ။")
        return

    audio_path = f"downloads/{target_audio_name}"
    download_file(target_audio_id, audio_path)

    print("Google Drive ၏ images ဖိုဒါကို စစ်ဆေးနေပါပြီ...")
    image_files = get_drive_files_via_api(IMAGES_DRIVE_FOLDER_ID)
    valid_images = [f for f in image_files if f["name"].lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    print(f"တွေ့ရှိရသော ပုံအရေအတွက်: {len(valid_images)} ခု")
    
    if not valid_images:
        print("Error: Google Drive ၏ images ဖိုဒါထဲတွင် ပုံများ မတွေ့ရှိရပါ။")
        return

    selected_images = random.sample(valid_images, min(3, len(valid_images)))
    
    local_image_paths = []
    for idx, img_info in enumerate(selected_images):
        img_path = f"downloads/img_{idx}.jpg"
        download_file(img_info["id"], img_path)
        local_image_paths.append(img_path)

    output_video = "final_output.mp4"
    temp_dir = "temp_processed"
    os.makedirs(temp_dir, exist_ok=True)

    processed_images = []
    for idx, img_path in enumerate(local_image_paths):
        out_img = os.path.join(temp_dir, f"img_{idx:03d}.png")
        resize_cmd = [
            "ffmpeg", "-y", "-i", img_path,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            out_img
        ]
        subprocess.run(resize_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processed_images.append(out_img)

    seconds_per_image = 10
    ffmpeg_cmd = ["ffmpeg", "-y"]
    for img in processed_images:
        ffmpeg_cmd.extend(["-loop", "1", "-t", str(seconds_per_image), "-i", img])
    
    ffmpeg_cmd.extend(["-i", audio_path])

    n = len(processed_images)
    filter_parts = [f"[{i}:v]scale=1280:720,setsar=1[v{i}]" for i in range(n)]
    concat_inputs = "".join([f"[v{i}]" for i in range(n)])
    filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[outv]")
    filter_parts_str = ";".join(filter_parts)

    ffmpeg_cmd.extend([
        "-filter_complex", filter_parts_str,
        "-map", "[outv]",
        "-map", f"{n}:a", "-c:a", "aac", "-shortest",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        output_video
    ])

    print("Video Render စတင်နေပါပြီ...")
    process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if process.returncode == 0:
        print("Video Render လုပ်ဆောင်ချက် အောင်မြင်စွာ ပြီးဆုံးပါပြီ!")
    else:
        print(f"Error ဖြစ်ပွားခဲ့သည်: {process.stderr[-500:]}")

if __name__ == "__main__":
    main()
