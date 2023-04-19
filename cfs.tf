# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Generates an archive of the source code compressed as a .zip file.

resource "google_storage_bucket" "ai_dubbing_bucket" {
  project = data.google_project.project.project_id
  name          = var.ai_dubbing_bucket_name
  location      = var.gcp_region
  force_destroy = false
  uniform_bucket_level_access = true
  depends_on    = [google_service_account.service_account,
                   google_project_service.enable_cloudfunctions]
}

data "archive_file" "source_generate_tts_files" {
    type        = "zip"
    source_dir  = "src/cfs/generate_tts_files"
    output_path = "/tmp/generate_tts_files.zip"
    depends_on   = []
}

data "archive_file" "source_generate_video_file" {
    type        = "zip"
    source_dir  = "src/cfs/generate_video_file"
    output_path = "/tmp/generate_video_file.zip"
    depends_on   = []
}

# Add source code zip to the Cloud Function's bucket
resource "google_storage_bucket_object" "generate_tts_files_zip" {
    source       = data.archive_file.source_generate_tts_files.output_path
    content_type = "application/zip"

    # Append to the MD5 checksum of the files's content
    # to force the zip to be updated as soon as a change occurs
    name         = "src-${data.archive_file.source_generate_tts_files.output_md5}.zip"
    bucket       = google_storage_bucket.ai_dubbing_bucket.name

    # Dependencies are automatically inferred so these lines can be deleted
    depends_on   = [
        google_storage_bucket.ai_dubbing_bucket,  # declared in `storage.tf`
    ]
}

# Add source code zip to the Cloud Function's bucket
resource "google_storage_bucket_object" "generate_video_file_zip" {
    source       = data.archive_file.source_generate_video_file.output_path
    content_type = "application/zip"

    # Append to the MD5 checksum of the files's content
    # to force the zip to be updated as soon as a change occurs
    name         = "src-${data.archive_file.source_generate_video_file.output_md5}.zip"
    bucket       = google_storage_bucket.ai_dubbing_bucket.name

    # Dependencies are automatically inferred so these lines can be deleted
    depends_on   = [
        google_storage_bucket.ai_dubbing_bucket,  # declared in `storage.tf`
    ]
}

# Create the Cloud function triggered by a `Finalize` event on the bucket
resource "google_cloudfunctions_function" "function_generate_tts_files" {
    depends_on            = [
        google_storage_bucket_object.generate_tts_files_zip,
        google_service_account.service_account,
        google_project_service.enable_cloudfunctions,
        google_project_service.enable_cloudbuild,
        google_storage_bucket.ai_dubbing_bucket
    ]
    name                  = "generate_tts_files"
    runtime               = "python38"

    environment_variables = {
        GCP_PROJECT = var.gcp_project,
        CONFIG_SPREADSHEET_ID = var.config_spreadsheet_id,
        CONFIG_SHEET_NAME = var.config_sheet_name,
        CONFIG_SHEET_RANGE = var.config_sheet_range,
        STATUS_COLUMN = var.status_column,
        TTS_FILE_COLUMN = var.tts_file_column,
        LAST_UPDATE_COLUMN = var.last_update_column,
        GENERATE_VIDEO_TOPIC = var.generate_video_file_trigger_pubsub_topic
    }

    # Get the source code of the cloud function as a Zip compression
    source_archive_bucket = google_storage_bucket.ai_dubbing_bucket.name
    source_archive_object = google_storage_bucket_object.generate_tts_files_zip.name

    # Must match the function name in the cloud function `main.py` source code
    entry_point           = "main"
    service_account_email = google_service_account.service_account.email
    available_memory_mb = 2048
    timeout = 540

    event_trigger {
      event_type = "google.pubsub.topic.publish"
      resource = google_pubsub_topic.generate_tts_files_trigger_topic.id
    }
}

# Create the Cloud function triggered by a `Finalize` event on the bucket
resource "google_cloudfunctions_function" "function_generate_video_file" {
    depends_on = [
        google_storage_bucket_object.generate_video_file_zip,
        google_service_account.service_account,
        google_project_service.enable_cloudfunctions,
        google_project_service.enable_cloudbuild,
        google_storage_bucket.ai_dubbing_bucket
    ]
    name = "generate_video_file"
    runtime = "python38"

    environment_variables = {
        GCP_PROJECT = var.gcp_project
        CONFIG_SPREADSHEET_ID = var.config_spreadsheet_id,
        CONFIG_SHEET_NAME = var.config_sheet_name,
        STATUS_COLUMN = var.status_column,
        LAST_UPDATE_COLUMN = var.last_update_column,
        FINAL_VIDEO_FILE_COLUMN = var.final_video_file_column
    }

    # Get the source code of the cloud function as a Zip compression
    source_archive_bucket = google_storage_bucket.ai_dubbing_bucket.name
    source_archive_object = google_storage_bucket_object.generate_video_file_zip.name

    # Must match the function name in the cloud function `main.py` source code
    entry_point = "main"
    available_memory_mb = 8192
    service_account_email = google_service_account.service_account.email
    timeout = 540

    event_trigger {
      event_type = "google.pubsub.topic.publish"
      resource = google_pubsub_topic.generate_video_file_trigger_topic.id
    }
}