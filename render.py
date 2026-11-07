import os
import glob
import random
import subprocess
import gdown

AUDIO_DRIVE_FOLDER_ID = os.environ.get("AUDIO_FOLDER_ID")
IMAGES_DRIVE_FOLDER_ID = os.environ.get("IMAGES_FOLDER_ID")

def main():
    print("ဗီဒီယို ဖန်တီးခြင်း လုပ်ငန်းစဉ် စတင်ပါပြီ...")

    os.makedirs("downloads/audio", exist_ok=True)
    os.makedirs("downloads/images", exist_ok=True)
    
    # ၁။ Google Drive ၏ audio ဖိုဒါမှ ဖိုင်များကို gdown ဖြင့် ဆွဲယူခြင်း
    print("Google Drive ၏ audio ဖိုဒါကို ဆွဲယူနေပါပြီ...")
    audio_url = f"https://drive.google.com/drive/folders/{AUDIO_DRIVE_FOLDER_ID}"
    gdown.download_folder(audio_url, output="downloads/audio", quiet=False, use_cookies=False)
    
    # downloads/audio ဖိုဒါအတွင်း မည်သည့်နေရာတွင်ရှိသည်ဖြစ်စေ အသံဖိုင်ကို ရှာဖွေခြင်း
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

    # ၂။ Google Drive ၏ images ဖိုဒါမှ ပုံများကို gdown ဖြင့် ဆွဲယူခြင်း
    print("Google Drive ၏ images ဖိုဒါကို ဆွဲယူနေပါပြီ...")
    images_url = f"https://drive.google.com/drive/folders/{IMAGES_DRIVE_FOLDER_ID}"
    gdown.download_folder(images_url, output="downloads/images", quiet=False, use_cookies=False)
    
    # downloads/images ဖိုဒါအတွင်း မည်သည့်နေရာတွင်ရှိသည်ဖြစ်စေ ပုံများကို ရှာဖွေခြင်း
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

    selected_images = valid_images[:10]

    # ၃။ ပုံများကို 1280x720 သို့ Resize လုပ်ခြင်း
    temp_img_dir = "temp_slideshow_imgs"
    os.makedirs(temp_img_dir, exist_ok=True)
    
    processed_images = []
    for idx, img_path in enumerate(selected_images):
        out_img = os.path.join(temp_img_dir, f"img_{idx:03d}.png")
        resize_cmd = [
            "ffmpeg", "-y", "-i", img_path,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            out_img
        ]
        subprocess.run(resize_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processed_images.append(out_img)

    # ၄။ FFmpeg ဖြင့် ဗီဒီယို Render လုပ်ခြင်း
    output_video = "final_output.mp4"
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

if __name
