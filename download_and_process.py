"""
Downloader
"""

import os
import json
import cv2
import logging


def download(video_path, ytb_id, proxy=None):
    """
    ytb_id: youtube_id
    save_folder: save video folder
    proxy: proxy url, defalut None
    """
    if proxy is not None:
        proxy_cmd = "--proxy {}".format(proxy)
    else:
        proxy_cmd = ""
    if not os.path.exists(video_path):
        down_video = " ".join(
            [
                "yt-dlp",
                proxy_cmd,
                "-f",
                "'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio'",
                "--skip-unavailable-fragments",
                "--merge-output-format",
                "mp4",
                "https://www.youtube.com/watch?v=" + ytb_id,
                "--output",
                video_path,
                "--external-downloader",
                "aria2c",
                "--external-downloader-args",
                '"-x 16 -k 1M"',
            ]
        )
        print(down_video)
        status = os.system(down_video)
        if status != 0:
            print(f"video not found: {ytb_id}")


def process_ffmpeg(raw_vid_path, save_folder, save_vid_name, bbox, time):
    """
    raw_vid_path:
    save_folder:
    save_vid_name:
    bbox: format: top, bottom, left, right. the values are normalized to 0~1
    time: begin_sec, end_sec
    """

    def secs_to_timestr(secs):
        hrs = secs // (60 * 60)
        min = (secs - hrs * 3600) // 60
        sec = secs % 60
        end = (secs - int(secs)) * 100
        return "{:02d}:{:02d}:{:02d}.{:02d}".format(
            int(hrs), int(min), int(sec), int(end)
        )

    def expand(bbox, ratio):
        top, bottom = max(bbox[0] - ratio, 0), min(bbox[1] + ratio, 1)
        left, right = max(bbox[2] - ratio, 0), min(bbox[3] + ratio, 1)

        return top, bottom, left, right

    def to_square(bbox):
        top, bottom, leftx, right = bbox
        h = bottom - top
        w = right - leftx
        c = min(h, w) // 2
        c_h = (top + bottom) / 2
        c_w = (leftx + right) / 2

        top, bottom = c_h - c, c_h + c
        leftx, right = c_w - c, c_w + c
        return top, bottom, leftx, right

    def denorm(bbox, height, width):
        top = round(bbox[0] * height)
        bottom = round(bbox[1] * height)
        left = round(bbox[2] * width)
        right = round(bbox[3] * width)
        return top, bottom, left, right

    out_path = os.path.join(save_folder, save_vid_name)
    cap = cv2.VideoCapture(raw_vid_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    top, bottom, left, right = to_square(denorm(expand(bbox, 0.02), height, width))
    start_sec, end_sec = time

    cmd = f"ffmpeg -i {raw_vid_path} -vf crop=w={right - left}:h={bottom - top}:x={left}:y={top} -ss {secs_to_timestr(start_sec)} -to {secs_to_timestr(end_sec)} -loglevel error {out_path}"
    os.system(cmd)
    return out_path


def load_data(file_path):
    with open(file_path) as f:
        data_dict = json.load(f)

    for key, val in data_dict.items():
        save_name = key + ".mp4"
        ytb_id = val["ytb_id"]
        time = val["duration"]["start_sec"], val["duration"]["end_sec"]
        bbox = [
            val["bbox"]["top"],
            val["bbox"]["bottom"],
            val["bbox"]["left"],
            val["bbox"]["right"],
        ]
        yield ytb_id, save_name, time, bbox


def extract_frames(input_file, output_dir):
    # replace spaces in the paths with "\ "
    input_file = input_file.replace(" ", "\ ")
    output_dir = output_dir.replace(" ", "\ ")

    # Create output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # ffmpeg commands
    get_duration = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {input_file}"
    get_framerate = f"ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 {input_file}"

    # get video duration and framerate
    duration = float(os.popen(get_duration).read())
    framerate = eval(os.popen(get_framerate).read())

    # calculate total frames and frame step
    total_frames = int(duration * framerate)
    frame_step = total_frames // 4

    # guard for very short or low fps videos
    if frame_step <= 0:
        frame_step = 1

    # extract frames
    extract_cmd = f'ffmpeg -i {input_file} -vf "select=not(mod(n\,{frame_step})),scale=512:-1" -vsync vfr {output_dir}/frame_%04d.png'
    os.system(extract_cmd)


if __name__ == "__main__":
    json_path = "celebvtext_info.json"  # json file path
    raw_vid_root = "./downloaded_celebvtext/raw/"  # download raw video path
    processed_vid_root = "./downloaded_celebvtext/processed/"  # processed video path
    proxy = None  # proxy url example, set to None if not use

    os.makedirs(raw_vid_root, exist_ok=True)
    os.makedirs(processed_vid_root, exist_ok=True)

    for vid_id, save_vid_name, time, bbox in load_data(json_path):
        raw_vid_path = os.path.join(raw_vid_root, vid_id + ".mp4")
        # Downloading is io bounded and processing is cpu bounded.
        # It is better to download all videos firstly and then process them via multiple cpu cores.
        # try:
        logging.debug(f"Downloading {vid_id}")
        # download(raw_vid_path, vid_id, proxy)

        logging.debug(f"Processing {vid_id}")
        process_ffmpeg(raw_vid_path, processed_vid_root, save_vid_name, bbox, time)

        logging.debug(f"Extracting key frames {vid_id}")
        processed_vid_path = os.path.join(processed_vid_root, save_vid_name)
        extract_frames(processed_vid_path, os.path.join(processed_vid_root, vid_id))

        # remove raw video
        os.remove(raw_vid_path)
        os.remove(processed_vid_path)

        # except:
        break
    # break
