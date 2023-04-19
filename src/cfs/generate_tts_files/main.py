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

# Config Line Fields
# campaign
# topic
# gcs_bucket
# video_file
# base_audio_file
# text
# voice_id
# millisecond_start_audio
# audio_encoding
# tts_file_url
# final_video_file_url
# status
# last_update

from typing import Any, Dict, List, Optional
from google.cloud.functions_v1.context import Context
from google.cloud import texttospeech
from google.cloud import storage
from google.cloud import pubsub_v1
from datetime import datetime

import json
import os.path
import base64

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# The ID and range of a sample spreadsheet.
GCP_PROJECT = os.getenv('GCP_PROJECT', '')
CONFIG_SPREADSHEET_ID = os.getenv('CONFIG_SPREADSHEET_ID', '')
CONFIG_SHEET_NAME = os.getenv('CONFIG_SHEET_NAME', 'config')
CONFIG_RANGE_NAME = os.getenv('CONFIG_RANGE_NAME', 'config!A1:M')
TTS_FILE_COLUMN = os.getenv('TTS_FILE_COLUMN', 'K')
STATUS_COLUMN = os.getenv('STATUS_COLUMN', 'L')
LAST_UPDATE_COLUMN = os.getenv('LAST_UPDATE_COLUMN', 'M')
GENERATE_VIDEO_TOPIC = os.getenv('GENERATE_VIDEO_TOPIC', 'generate_video_trigger')

def main(event: Dict[str, Any], context=Optional[Context]):
  """
  Reads config and generate TTS files to finally trigger the video generation.

  Args:
    event (dict):  The dictionary with data specific to this type of event. The
      `data` field contains the PubsubMessage message. The `attributes` field
      will contain custom attributes if there are any.
    context (google.cloud.functions.Context): The Cloud Functions event
      metadata. The `event_id` field contains the Pub/Sub message ID. The
      `timestamp` field contains the publish time.
  """
  del context # unused
  del event # unused
  lines = _read_config_from_google_sheet(CONFIG_SPREADSHEET_ID,CONFIG_SHEET_NAME)
  lines = _generate_tts(lines)

def _read_config_from_google_sheet(sheet_id, sheet_name) -> List[Dict]:
  """
  Reads all the lines in a Google Sheet having the first row the name of the fields and outputs an array of dicts.

  Args:
    sheet_id: The ID of the Google Sheet.
    sheet_name: The name of the sheet in the Google Sheet.

  Returns:
    An array of dicts, where each dict represents a row in the Google Sheet.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  rows = []
  try:
      service = build('sheets', 'v4', credentials=None)

      # Call the Sheets API
      sheet = service.spreadsheets()
      result = sheet.values().get(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                  range=CONFIG_RANGE_NAME).execute()
      values = result.get('values', [])

      # Create an array of dicts, where each dict represents a row in the Google Sheet.
      if not values:
        print('No values')
        return rows

      headers = values[0]
      i = 2
      for row in values[1:]:
          if row:
              new_row = {field: value for field, value in zip(headers, row)}
              new_row['index'] = i
              rows.append(new_row)
              i = i + 1

  except HttpError as err:
      print(err)

  return rows

def _generate_tts(lines: List[Dict]) -> List[Dict]:
 """
  For each line makes a call to Google TTS AI to generate the audio files and store them in GCS

  Args:
    lines: Dict object containing all
    sheet_name: The name of the sheet in the Google Sheet.

  Returns:
    An array of dicts, where each dict represents a row in the Google Sheet.
  """
 for line in lines:
    if line:
      try:
        today =  datetime.today().strftime('%Y%m%d')
        file_name = f"output/{today}/{_build_file_name(line)}"
        _tts_api_call(line, file_name)
        line['status'] = 'TTS OK'
        line['tts_file_url'] = file_name
        _call_video_generation(line)

      except Exception as e:
        line['status'] = e
        line['tts_file_url'] = 'N/A'
        print(e)

      _update_sheet_line(line)

 return lines


def _tts_api_call(line: Dict, file_name: str):
  """
  It call the TTS API with the parameters received in the line parameter

  Args:
    line: Dict object containing the fields to generate the tts audio file
  """

  # Instantiates a client
  client = texttospeech.TextToSpeechClient()
  # Set the text input to be synthesized
  synthesis_input = texttospeech.SynthesisInput(ssml=line['text'])

  # Build the voice request, select the language code ("en-US") and the ssml
  # voice gender ("neutral")
  voice_id = line['voice_id'].split('##')[0]
  language_code = line['voice_id'][:5]
  voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_id)

  # Select the type of audio file you want returned
  audio_config = texttospeech.AudioConfig(
      audio_encoding=eval('texttospeech.AudioEncoding.' + line['audio_encoding'])
  )

  # Perform the text-to-speech request on the text input with the selected
  # voice parameters and audio file type
  response = client.synthesize_speech(
      input=synthesis_input, voice=voice, audio_config=audio_config
  )

  # The response's audio_content is binary.
  # _write_to_local_file(file_name, response)

  _write_to_gcs(line['gcs_bucket'], file_name, response)
   
def _write_to_gcs(gcs_bucket: str, file_name: str, response):
  """
  Writes the contents of response into file_name as binary in the gcs_bucket

  Args:
    gcs_bucket: name of the gcs bucket
    file_name: the name of the file to write
    response: the object containing the binary data to write
  """

  storage_client = storage.Client()
  bucket = storage_client.bucket(gcs_bucket)
  blob = bucket.blob(file_name)

  # Mode can be specified as wb/rb for bytes mode.
  # See: https://docs.python.org/3/library/io.html
  with blob.open("wb") as f:
      f.write(response.audio_content)

def _build_file_name(line: Dict) -> str:
  """
  It builds the file name based on the configuration fields

  Args:
    line: Dict object containing the fields to generate the tts audio file

  Returns:
    A string with the name in low case
  """

  name = (
     f"{line['campaign']}"
     f"-{line['topic']}"
     f"-{line['voice_id']}"
     f".{line['audio_encoding']}"
  )

  return name.lower()

def _call_video_generation(line: Dict):
  """
  It triggers the video generation call function passing all the info required

  Args:
    line: Dict object containing the fields to generate the video file
  """
  _send_pub_sub(line, GENERATE_VIDEO_TOPIC)

def _update_sheet_line(line: Dict):
  """
  Updates the line in the Google Spreadsheet defined in the global variabl.

  Args:
    line: Dict containing all the relevant info.
  """

  try:
      service = build('sheets', 'v4', credentials=None)
      index = line['index']
      status_range = f"{CONFIG_SHEET_NAME}!{STATUS_COLUMN}{index}:{STATUS_COLUMN}{index}"
      tts_file_range = f"{CONFIG_SHEET_NAME}!{TTS_FILE_COLUMN}{index}:{TTS_FILE_COLUMN}{index}"
      last_update_range = f"{CONFIG_SHEET_NAME}!{LAST_UPDATE_COLUMN}{index}:{LAST_UPDATE_COLUMN}{index}"

      body1 = {
        'values' : [[str(line['status'])],],
        'majorDimension' : 'COLUMNS'
        }

      body2 = {
        'values' : [[str(line['tts_file_url'])],],
        'majorDimension' : 'COLUMNS'
        }

      now = datetime.now()
      body3 = {
        'values' : [[str(now.strftime("%Y/%m/%d, %H:%M:%S"))],],
        'majorDimension' : 'COLUMNS'
        }
      # Call the Sheets API

      sheet = service.spreadsheets()
      sheet.values().update(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                    range=status_range,
                                    valueInputOption='RAW',
                                    body=body1).execute()

      sheet.values().update(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                    range=tts_file_range,
                                    valueInputOption='RAW',
                                    body=body2).execute()

      sheet.values().update(spreadsheetId=CONFIG_SPREADSHEET_ID,
                                    range=last_update_range,
                                    valueInputOption='RAW',
                                    body=body3).execute()
  except HttpError as err:
      print(err)


def _send_pub_sub(message: Dict, topic: str):
  """
  It sends a message to the pubsub topic

  Args:
    message: Dict object containing the info to send to the topic
    topic: string containing the name of the topic
  """
  publisher = pubsub_v1.PublisherClient()
  topic_path = publisher.topic_path(GCP_PROJECT, topic)
  msg_json = json.dumps(message)

  unused_msg_id = publisher.publish(
      topic_path,
      data=bytes(msg_json, 'utf-8'),
    ).result()

if __name__ == '__main__':

    msg_data = {}
    msg_data = base64.b64encode(bytes(json.dumps(msg_data).encode('utf-8')))
    print(msg_data)
    main(
      event={
          'data': msg_data,
          'attributes': {
          }
      },
      context=None)

# [END main]

