# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START main]

from google.cloud import storage
from mutagen.mp3 import MP3
from typing import Any, Dict, Optional
from google.cloud.functions_v1.context import Context
from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

import os
import string
import random
import json
import base64

GCP_PROJECT = os.getenv('GCP_PROJECT', '')
CONFIG_SPREADSHEET_ID = os.getenv('CONFIG_SPREADSHEET_ID', '')
CONFIG_SHEET_NAME = os.getenv('CONFIG_SHEET_NAME', 'config')
CONFIG_RANGE_NAME = os.getenv('CONFIG_RANGE_NAME', 'config!A1:L')
FINAL_VIDEO_FILE_COLUMN = os.getenv('FINAL_VIDEO_FILE_COLUMN', 'K')
STATUS_COLUMN = os.getenv('STATUS_COLUMN', 'L')
LAST_UPDATE_COLUMN = os.getenv('LAST_UPDATE_COLUMN', 'M')

def _get_mp3_length(path: str):
    """Returns the length of a MP3 file in seconds.

    Args:
      path: Path to the MP3 file.
    """
    try:
        audio = MP3(path)
        length = audio.info.length
        return length
    except:
        return None


def _copy_file_from_gcs(gcs_bucket: str, source_blob_name: str, destination_local_filename: str):
    """Copies a file from Google Cloud Storage to a temporary local filename.

    Args:
      gcs_bucket: string containing the bucket name.
      source_blob_name: Name of the source blob containing the file.
      destination_local_filename: Name of the local file that will be written.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_local_filename)


def _copy_file_to_gcs(gcs_bucket: str, source_local_filename: str, destination_blob_name: str):
    """Copies a file to Google Cloud Storage from a temporary local filename.

    Args:
      gcs_bucket: string containing the bucket name.
      source_local_filename: Name of the local file that will be copied.
      destination_blob_name: Name of the blob to be created in GCS.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(destination_blob_name)
    print(gcs_bucket)
    print(source_local_filename)
    print(destination_blob_name)
    print('Checking if blob exists')
    if blob.exists():
        print('Deleting existing target file')
        blob.delete()
    blob.upload_from_filename(source_local_filename)


def _mix_video_and_speech(config: Dict): #, video_file, speech_file,destination_video_name, voice_delay):
    """Mixes a generated speech file with the audio of the specified video.

    Args:
      config: Dictionary containing the configuration information.
    """
    # Generate a 10 characters long random string (rnd)
    random_string = ''.join(random.choices(
        string.ascii_lowercase + string.digits, k=12))

    # Copy video_file from blob to /tmp/video[rnd].mp4
    source_video_input = '/tmp/video_{random_string}.mp4'.format(
        random_string=random_string)
    input_video_file = f"{config['video_file']}"
    print(input_video_file)
    _copy_file_from_gcs(config['gcs_bucket'], input_video_file, source_video_input)

    # Copy base_audio_file from blob to /tmp/base_audio_[rnd].{sound_extension}
    sound_extension = config['base_audio_file'].split(".")[1]
    source_audio_input = f"/tmp/base_audio_{random_string}.{sound_extension}"
    _copy_file_from_gcs(config['gcs_bucket'], config['base_audio_file'], source_audio_input)

    # Copy speech_file from blob to /tmp/speech[rnd].mp3
    source_speech_input = '/tmp/speech_{random_string}.mp4'.format(
        random_string=random_string)
    _copy_file_from_gcs(config['gcs_bucket'], config['tts_file_url'], source_speech_input)

    # Generate and run mix command to generate the output video file
    generated_video_file = '/tmp/output_{random_string}.mp4'.format(
        random_string=random_string)

    # Calculate when the original audio should be adjusted during and
    # after the voice dub section
    audio_down_start = int(config['millisecond_start_audio'])/1000
    voice_dub_length = _get_mp3_length(source_speech_input)
    print('Voice Dub length is {voice_dub_length}'.format(
        voice_dub_length=voice_dub_length))
    audio_down_end = audio_down_start + voice_dub_length

    ffmpeg_mix_command = (
                    "ffmpeg "
                    "-loglevel error "
                    f"-i {source_video_input} -i {source_audio_input} -i {source_speech_input} "
                    "-filter_complex "
                    f"\"[2:a] adelay={config['millisecond_start_audio']}|{config['millisecond_start_audio']} [voice_dub];"
                    f"[1:a] volume=0.9:enable='between(t,{audio_down_start},{audio_down_end})' [original_audio];"
                    f"[original_audio] volume=0.9:enable='gt(t,{audio_down_end})' [original_audio];"
                    f"[voice_dub][original_audio] amix=duration=longest [audio_out]"
                    "\" "
                    f"-map 0:v -map \"[audio_out]\" -y {generated_video_file}"
                    )
    print(f'Running command: {ffmpeg_mix_command}')
    try:
        os.system(ffmpeg_mix_command)
        print('Copying output file to GCS')
        today =  datetime.today().strftime('%Y%m%d')
        target_video_file_name = f"output/{today}/{_build_file_name(config)}"
        print(target_video_file_name)
        # Copy the generated video file to the target GCS bucket
        _copy_file_to_gcs(config['gcs_bucket'], generated_video_file, target_video_file_name)
        config['status'] = 'Video OK'
        config['final_video_file_url'] = f"gs://{config['gcs_bucket']}/{target_video_file_name}"

    except Exception as e:
        config['status'] = e
        config['final_video_file_url'] = "N/A"

    _update_sheet_line(config)

    # Cleanup temp files
    print('Cleaning up')
    os.remove(source_video_input)
    os.remove(source_speech_input)
    os.remove(generated_video_file)

def main(event: Dict[str, Any], context=Optional[Context]):
    """Mixes a generated speech audio file into an input video.
    Args:
      event (dict):  The dictionary with data specific to this type of event. The
        `data` field contains the PubsubMessage message. The `attributes` field
        will contain custom attributes if there are any.
      context (google.cloud.functions.Context): The Cloud Functions event
        metadata. The `event_id` field contains the Pub/Sub message ID. The
        `timestamp` field contains the publish time.
    """

    del context  # Unused
    data = base64.b64decode(event['data']).decode('utf-8')
    config = json.loads(data)
    _mix_video_and_speech(config)
    _update_sheet_line(config)
    print('Process completed')
    return 'done'


def _build_file_name(config: Dict) -> str:
    """
    It builds the file name based on the configuration fields

    Args:
      config: Dict object containing the fields to generate the video file

    Returns:
      A string with the name in low case
    """

    name = (
     f"{config['campaign']}"
     f"-{config['topic']}"
     f"-{config['voice_id']}.mp4"
     )

    return name.lower()

def _update_sheet_line(line: Dict):
  """
  Updates the line in the Google Spreadsheet defined in the global variabl.

  Args:
    line: Dict containing all the relevant info.
  """

  try:
      service = build('sheets', 'v4', credentials=None)
      index = line['index']
      status_range = f'{CONFIG_SHEET_NAME}!{STATUS_COLUMN}{index}:{STATUS_COLUMN}{index}'
      final_video_file_range = f'{CONFIG_SHEET_NAME}!{FINAL_VIDEO_FILE_COLUMN}{index}:{FINAL_VIDEO_FILE_COLUMN}{index}'
      last_update_range = f"{CONFIG_SHEET_NAME}!{LAST_UPDATE_COLUMN}{index}:{LAST_UPDATE_COLUMN}{index}"

      body1 = {
        'values' : [[str(line['status'])],],
        'majorDimension' : 'COLUMNS'
        }

      body2 = {
        'values' : [[str(line['final_video_file_url'])],],
        'majorDimension' : 'COLUMNS'
        }

      now = datetime.now()
      body3 = {
        'values' : [[now.strftime("%Y/%m/%d, %H:%M:%S")],],
        'majorDimension' : 'COLUMNS'
        }
      # Call the Sheets API

      sheet = service.spreadsheets()
      sheet.values().update(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                    range=status_range,
                                    valueInputOption='RAW',
                                    body=body1).execute()

      sheet.values().update(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                    range=final_video_file_range,
                                    valueInputOption='RAW',
                                    body=body2).execute()

      sheet.values().update(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                    range=last_update_range,
                                    valueInputOption='RAW',
                                    body=body3).execute()

  except HttpError as err:
      print(err)

if __name__ == '__main__':
    config = {
        'source_bucket_name': 'videodub_test_input',
        'target_bucket': 'videodub_test_output'
    }

    msg_data = {'campaign': 'summer',
                'topic': 'outdoor',
                'video_file': 'input/bumper_master.mp4',
                'base_audio_file': 'input/soundtrack_bumper.wav',
                'text': '<speak>\n  Here are <say-as interpret-as="characters">SSML</say-as></speak>',
                'voice_id': 'en-US-Standard-I',
                'millisecond_start_audio': '0',
                'audio_encoding': 'MP3',
                'gcs_bucket': 'videodub_test_input',
                'index': 1,
                'status': 'OK',
                'tts_file_url': 'output/20230419/summer-outdoor-en-us-standard-i##male.mp3'}

    msg_data = base64.b64encode(bytes(json.dumps(msg_data).encode('utf-8')))

    main(
      event={
          'data': msg_data,
          'attributes': {
              'forwarded': 'true'
          }
      },
      context=None)

# [END main]