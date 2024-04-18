import sys
import youtube_dl
from pydub import AudioSegment
from io import BytesIO
import boto3
import os

def download_and_combine_audio(playlist_url, output_filename):
    try:
        print("Initializing S3 client...")
        # Initialize S3 client
        s3 = boto3.client('s3')

        print("Configuring youtube_dl...")
        # Configure youtube_dl
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'tmp/%(title)s.%(ext)s', 
            'quiet': False,  # Enable logging from youtube_dl
        }

        print("Downloading videos from playlist...")
        # Download videos from playlist
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            playlist_items = info['entries']

            combined_audio = None
            for video in playlist_items:
                video_url = video['url']
                print(f"Downloading audio from {video_url}...")
                with ydl:
                    audio_bytes = ydl.extract_info(video_url, download=True)
                    print(audio_bytes)
                    audio_path = os.path.normpath('/tmp/' + audio_bytes['title'] + '.mp3')
                    if os.path.exists(audio_path):
                        audio = AudioSegment.from_file(audio_path, format="mp3")
                        if combined_audio is None:
                            combined_audio = audio
                        else:
                            combined_audio += audio
                    else:
                        print(f"Audio file not found: {audio_path}")

        if combined_audio is not None:
            # Convert combined audio to bytes
            combined_audio_bytes = BytesIO()
            combined_audio.export(combined_audio_bytes, format="mp3")
            combined_audio_bytes.seek(0)
            print("Combined audio created")

            print("Uploading combined audio to S3...")
            # Upload combined audio to S3
            bucket_name = 'public-blob'
            object_key = output_filename
            s3.upload_fileobj(combined_audio_bytes, bucket_name, object_key)

            # Return S3 URL of combined audio
            s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
            print(f"Audio uploaded to S3: {s3_url}")
        else:
            print("No audio files downloaded.")
    except Exception as e:
        # Handle any exceptions and return an error response
        error_message = str(e)
        print(f"Error: {error_message}")

if __name__=="__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <playlist_url> <output_filename>")
        sys.exit(1)

    playlist_url = sys.argv[1]
    output_filename = sys.argv[2]
    download_and_combine_audio(playlist_url, output_filename)
