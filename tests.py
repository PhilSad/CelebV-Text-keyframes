import os
import download_and_process


def test_extract_keyframes():
    input_file = "./downloaded_celebvtext/raw/file_example_MP4_480_1_5MG.mp4"
    output_dir = "./downloaded_celebvtext/processed/file_example_MP4_480_1_5MG/"
    download_and_process.extract_frames(input_file, output_dir)


def test_process():
    download_and_process.process_ffmpeg(
        "./downloaded_celebvtext/raw/sample-mp4-file-small.mp4",
        "./downloaded_celebvtext/processed/",
        "sample-mp4-file-small.mp4",
        [0.0, 0.5, 0.0, 0.5],
        [0.0, 0.5],
    )


if __name__ == "__main__":
    test_process()
