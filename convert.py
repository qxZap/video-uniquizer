import os
import time
import random
import ffmpeg
import concurrent.futures
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

# Configuration settings
MAX_WORKERS = 5
config = {
    "resolution": (110, 120, "int"),
    "gamma": (0.95, 1.05, "float"),
    "saturation": (0.95, 1.05, "float"),
    "brightness": (-0.1, 0.1, "float"),
    "contrast": (0.90, 1.05, "float"),
    "hue": (0, 10, "int"),
    "sharpness": (0.0, 1.0, "float"),
    "noise": (0.02, 0.04, "float"),
    "crop": (0.9, 1.00, "float"),
    "volume": (1, 5, "int"),
    "speed": (0.95, 1.05, "float"),
    "frame_skip": (0, 1, "int"),
    "time_stretch": (0.95, 1.05, "float"),
    "bg_volume": (0.2, 0.5, "float")
}

# Place your videos here
INPUT_FOLDER = 'input'

# Video edited videos will end up in this folder
VIDEO_EDIT_FOLDER = 'edited_videos'

# Video edited with background songs will end up in this folder
VIDEO_WITH_SONGS = 'edited_with_songs'

# Temporary folder, don't delete it, don't mess with it
TEMP_FOLDER = 'tmp'

# Folder where songs are being stored
SONGS_FOLDER = 'songs_background'

# This is in case you want a prefix to the video title, just in case
VIDEO_PREFIX = ''

os.makedirs(VIDEO_EDIT_FOLDER, exist_ok=True)
os.makedirs(VIDEO_WITH_SONGS, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

def get_audio_duration(audio_path):
    retries = 5
    for _ in range(retries):
        try:
            with AudioFileClip(random_song) as audio_clip:
                return audio_clip.duration
        except FileNotFoundError as e:
            print(f"File not found: {e}")
            sleep_time = random.uniform(1, 4)
            print(f"Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        except Exception as e:
            print(f"Error occurred: {e}")
            sleep_time = random.uniform(1, 4)
            print(f"Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
    raise Exception(f"Could not retrieve audio duration after {retries} attempts.")

def generate_random_values(config):
    """Generates random values based on the given configuration."""
    rand_values = {}
    for key, (min_val, max_val, val_type) in config.items():
        if val_type == "int":
            rand_values[key] = random.randint(min_val, max_val)
        elif val_type == "float":
            rand_values[key] = random.uniform(min_val, max_val)
    return rand_values

def combineVideoWithAudio(video_path, audio_path, audio_volume, output_video):
    audioclip = AudioFileClip(audio_path)
    audioclip.with_volume_scaled(audio_volume)
    videoclip = VideoFileClip(video_path)

    new_audioclip = CompositeAudioClip([videoclip.audio, audioclip])
    videoclip.audio = new_audioclip
    videoclip.write_videofile(output_video)

def get_random_song():
    """Returns a random song file from the 'songs_background' folder."""
    song_files = [f for f in os.listdir(SONGS_FOLDER) if f.endswith('.mp3')]
    return os.path.join(SONGS_FOLDER, random.choice(song_files)) if song_files else None

def process_video(filename, random_song, song_duration):
    input_filename = os.path.join(INPUT_FOLDER, filename)
    output_filename = os.path.join(VIDEO_EDIT_FOLDER, f'{VIDEO_PREFIX}{os.path.splitext(filename)[0]}.mp4')

    rand_values = generate_random_values(config)
    rand_bg_volume = rand_values["bg_volume"]

    # Apply video filters using ffmpeg
    ffmpeg.input(input_filename).output(output_filename,
                                        vf=f"eq=gamma={rand_values['gamma']}:saturation={rand_values['saturation']}:brightness={rand_values['brightness']}:contrast={rand_values['contrast']}," 
                                           f"hue=h={rand_values['hue']}," 
                                           f"unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount={rand_values['sharpness']}," 
                                           f"noise=alls={rand_values['noise']}:allf=t," 
                                           f"crop={rand_values['crop']}*in_w:{rand_values['crop']}*in_h",
                                        af=f"volume={rand_values['volume']},atempo={rand_values['speed']}").run(overwrite_output=True)

    if random_song:
        output_with_song_filename = os.path.join(VIDEO_WITH_SONGS, f'{VIDEO_PREFIX}{os.path.splitext(filename)[0]}.mp4')

        with VideoFileClip(output_filename) as video_clip:
            video_duration = video_clip.duration

        if song_duration > video_duration:
            random_start = random.uniform(0, song_duration - video_duration)
        else:
            random_start = 0

        temp_audio_file = os.path.join(TEMP_FOLDER, f"temp_trimmed_audio_{filename}.mp3")
        ffmpeg.input(random_song, ss=random_start).output(temp_audio_file, t=video_duration, af=f"volume={rand_bg_volume}").run(overwrite_output=True)

        combineVideoWithAudio(output_filename, temp_audio_file, rand_bg_volume, output_with_song_filename)
        os.remove(temp_audio_file)

task_map = []

for f in os.listdir(INPUT_FOLDER):
    if f.endswith('.mp4'):
        random_song = get_random_song()
        song_duration = get_audio_duration(random_song)
        task_map.append({
            'filename':f,
            'random_song': random_song,
            'song_duration': song_duration
        })

with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    for task in task_map:
        future = executor.submit(process_video, task['filename'], task['random_song'], task['song_duration'])
    result = future.result()

print("All videos processed!")
