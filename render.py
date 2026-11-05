import os
import json
import random
import glob
import subprocess
import urllib.request
import urllib.parse
import re

AUDIO_DRIVE_FOLDER_ID = os.environ.get("AUDIO_FOLDER_ID")
IMAGES_DRIVE_FOLDER_ID = os.environ.get("IMAGES_FOLDER_ID")

def load_state():
    if os.path.exists("state.json"):
        with open("state.json", "r") as f:
            return json.load(f)
    return {"current_index": 1}

def save_state(state):
    with open("state.json", "w") as f:
        json.dump(state, f, indent=4)

def get_drive_files_in_folder(folder_id):
    """ Google Drive Public Folder ထဲရှိ ဖိုင်များ၏ ID နှင့် နာမည်များကို ရယူခြင်း """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
            
        # Regex ဖြင့် Drive ထဲရှိ file ID နှင့် နာမည်များကို ရှာဖွေခြင်း
        matches = re.findall(r'\["([a-zA-Z0-9_-]{25,})",\s*"([^"]+)"', html_content)
        files = []
        seen_ids = set()
        for file_id, name in matches:
            if file_id not in seen_ids and file_id != folder_id:
                seen_ids.add(file_id)
                files.append({"id": file_id, "name": name})
        return files
    except Exception as e:
        print(f"Drive ဖိုင်များကို ဖတ်ရှုရာတွင် အမှားအယွင်းရှိသည်: {e}")
        return []

def download_file(file_id, output_path):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    # Cookie ရယူရန် URL သို့ ပထမဦးစွာ Request ပို့ခြင်း
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    urllib.request.install_opener(opener)
    
    try:
        response = opener.open(url)
        # Confirm token ပါရှိမရှိ စစ်ဆေးခြင်း (ကြီးမားသောဖိုင်များအတွက်)
        content = response.read()
        with open(output_path, "wb") as f:
            f.write(content)
        print(f"ဒေါင်းလုဒ်လုပ်ပြီးပါပြီ: {output_path}")
    except Exception as e:
        print(f"ဒေါင်းလုဒ်ဆွဲ၍ မရပါ ({output_path}): {e}")

def main():
    print("ဗီဒီယို ဖန်တီးခြင်း လုပ်ငန်းစဉ် စတင်ပါပြီ...")
    
    state = load_state()
    current_index = state.get("current_index", 1)
    
    if current_index > 30:
        current_index = 1

    audio_filename_target = f"{current_index:02d}.mp3"
    print(f"ယနေ့ ရှာဖွေမည့် အသံဖိုင်: {audio_filename_target} (Index: {current_index})")

    os.makedirs("downloads", exist_ok=True)
    
    # ၁။ Audio ဖိုင်များကို Drive မှ လှမ်းဆွဲရန် ရှာဖွေခြင်း
    print("Google Drive မှ အသံဖိုင်များကို စစ်ဆေးနေပါပြီ...")
    audio_files = get_drive_files_in_folder(AUDIO_DRIVE_FOLDER_ID)
    
    target_audio_id = None
    for f in audio_files:
        if audio_filename_target in f["name"]:
            target_audio_id = f["id"]
            break
            
    if not target_audio_id and audio_files:
        # အကယ်၍ တိကျသော နာမည်မတွေ့ပါက Index အလိုက် ပထမဆုံးရရှိနိုင်သည့် အသံကို ယူမည်
        target_audio_id = audio_files[min(current_index - 1, len(audio_files) - 1)]["id"]

    if not target_audio_id:
        print("Error: Google Drive ၏ audio ဖိုဒါထဲတွင် အသံဖိုင် မတွေ့ရှိရပါ။")
        return

    audio_path = "downloads/audio.mp3"
    download_file(target_audio_id, audio_path)

    # ၂။ Images ဖိုင်များကို Drive မှ လှမ်းဆွဲရန်
    print("Google Drive မှ ပုံများကို စစ်ဆေးနေပါပြီ...")
    image_files = get_drive_files_in_folder(IMAGES_DRIVE_FOLDER_ID)
    
    valid_images = [f for f in image_files if f["name"].lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not valid_images:
        print("Error: Google Drive ၏ images ဖိုဒါထဲတွင် ပုံများ မတွေ့ရှိရပါ။")
        return

    # ပုံများကို ကျပန်း (Random) ၃ ပုံ ရွေးထုတ်မည် (သို့မဟုတ် လိုသလောက်)
    selected_images = random.sample(valid_images, min(3, len(valid_images)))
    
    local_image_paths = []
    for idx, img_info in enumerate(selected_images):
        img_path = f"downloads/img_{idx}.jpg"
        download_file(img_info["id"], img_path)
        local_image_paths.append(img_path)

    print(f"စုစုပေါင်း ကျပန်းရွေးချယ်ထားသော ပုံအရေအတွက်: {len(local_image_paths)}")

    # ၃။ FFmpeg ဖြင့် ဗီဒီယို တည်ဆောက်ခြင်း
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
        # ၄။ State ကို နောက်တစ်ရက်အတွက် တိုးပေးခြင်း (+1)
        state["current_index"] = current_index + 1
        save_state(state)
        print(f"State အသစ်သို့ ပြောင်းလဲပြီးပါပြီ: Index {current_index + 1}")
    else:
        print(f"Error ဖြစ်ပွားခဲ့သည်: {process.stderr[-500:]}")

if __name__ == "__main__":
    main()
