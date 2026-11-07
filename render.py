import os
import glob
import subprocess
import gdown

AUDIO_DRIVE_FOLDER_ID = os.environ.get("AUDIO_FOLDER_ID")
IMAGES_DRIVE_FOLDER_ID = os.environ.get("IMAGES_FOLDER_ID")

# GitHub GUI Form မှ ပို့လိုက်သော တန်ဖိုးများကို ရယူခြင်း (မရှိပါက Default အနေဖြင့် ၈ စက္ကန့်နှင့် ultrafast ကို သုံးမည်)
seconds_per_image = int(os.environ.get("INPUT_SECONDS", 8))
video_preset = os.environ.get("INPUT_PRESET", "ultrafast")

def main():
    print(f"ဗီဒီယို ဖန်တီးခြင်း စတင်ပါပြီ... (ပုံတစ်ပုံချင်းစီ: {seconds_per_image} စက္ကန့်၊ Preset: {video_preset})")

    os.makedirs("downloads/audio", exist_ok=True)
    os.makedirs("downloads/images", exist_ok=True)
    
    # ၁။ Google Drive ၏ audio ဖိုဒါမှ အသံဖိုင်ကို ဆွဲယူခြင်း
    print("Google Drive ၏ audio ဖိုဒါကို ဆွဲယူနေပါပြီ...")
    audio_url = f"https://drive.google.com/drive/folders/{AUDIO_DRIVE_FOLDER_ID}"
    gdown.download_folder(audio_url, output="downloads/audio", quiet=False, use_cookies=False)
    
    audio_files = sorted(
        glob.glob(os.path.join("downloads/audio", "**", "*.mp3"), recursive=True) +
        glob.glob(os.path.join("downloads/audio", "**", "*.wav"), recursive=True) +
        glob.glob(os.path.join("downloads/audio", "**", "*.m4a"), recursive=True) +
        glob.glob(os.path.join("downloads/audio", "**", "*.ogg"), recursive=True) +
        glob.glob(os.path.join("downloads/audio", "*.mp3")) +
        glob.glob(os.path.join("downloads/audio", "*.wav"))
    )

    if not audio_files:
        print("Error: Google Drive ၏ audio ဖိုဒါထဲတွင် အသံဖိုင် မတွေ့ရှိရပါ။")
        return

    audio_path = audio_files[0]
    print(f"အသုံးပြုမည့် အသံဖိုင်: {audio_path}")

    # ၂။ Google Drive ၏ images ဖိုဒါမှ ပုံများကို ဆွဲယူခြင်း
    print("Google Drive ၏ images ဖိုဒါကို ဆွဲယူနေပါပြီ...")
    images_url = f"https://drive.google.com/drive/folders/{IMAGES_DRIVE_FOLDER_ID}"
    gdown.download_folder(images_url, output="downloads/images", quiet=False, use_cookies=False)
    
    valid_images = sorted(
        glob.glob(os.path.join("downloads/images", "**", "*.png"), recursive=True) +
        glob.glob(os.path.join("downloads/images", "**", "*.jpg"), recursive=True) +
        glob.glob(os.path.join("downloads/images", "**", "*.jpeg"), recursive=True) +
        glob.glob(os.path.join("downloads/images", "**", "*.webp"), recursive=True) +
        glob.glob(os.path.join("downloads/images", "*.png")) +
        glob.glob(os.path.join("downloads/images", "*.jpg")) +
        glob.glob(os.path.join("downloads/images", "*.jpeg"))
    )

    print(f"တွေ့ရှိရသော ပုံအရေအတွက်: {len(valid_images)} ခု")
    
    if not valid_images:
        print("Error: Google Drive ၏ images ဖိုဒါထဲတွင် ပုံများ မတွေ့ရှိရပါ။")
        return

    # ၃။ ပုံများကို 1280x720 သို့ Resize လုပ်ခြင်း
    temp_img_dir = "temp_slideshow_imgs"
    os.makedirs(temp_img_dir, exist_ok=True)
    
    processed_images = []
    for idx, img_path in enumerate(valid_images):
        out_img = os.path.join(temp_img_dir, f"img_{idx:03d}.png")
        resize_cmd = [
            "ffmpeg", "-y", "-i", img_path,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            out_img
        ]
        subprocess.run(resize_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processed_images.append(out_img)

    # ၄။ FFmpeg ဖြင့် ဗီဒီယို Render လုပ်ခြင်း (ပုံများကို Loop ပတ်၍ အသံဖိုင်အရှည်အတိုင်း ထုတ်မည်)
    output_video = "final_output.mp4"
    
    ffmpeg_cmd = ["ffmpeg", "-y"]
    ffmpeg_cmd.extend(["-stream_loop", "-1"]) # ပုံများကုန်ပါက အစမှ ပြန်စရန်
    
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
        "-map", f"{n}:a", 
        "-c:a", "aac", 
        "-shortest", # အသံဖိုင် ပြီးဆုံးသည့်အချိန်တွင် ဗီဒီယိုပါ တခါတည်း ပြီးဆုံးမည်
        "-c:v", "libx264", "-preset", video_preset, "-pix_fmt", "yuv420p",
        output_video
    ])

    print("Video Render စတင်နေပါပြီ...")
    process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=Type if 'Type' in globals() else text := True)

    if process.returncode == 0:
        print("Video Render လုပ်ဆောင်ချက် အောင်မြင်စွာ ပြီးဆုံးပါပြီ!")
    else:
        print(f"Error ဖြစ်ပွားခဲ့သည်: {process.stderr[-500:]}")

if __name__ == "__main__":
    main()
