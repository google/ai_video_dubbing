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
# --------------------------------------------------
# Set these before applying the configuration
# --------------------------------------------------

variable "gcp_project" {
  type        = string
  description = "Google Cloud Project ID where the artifacts will be deployed"
  default     = "my-project"
}

variable "gcp_region" {
  type        = string
  description = "Google Cloud Region"
  default     = "europe-west1"
}

variable "ai_dubbing_sa" {
  type        = string
  description = "Service Account for the deployment"
  default     = "ai-dubbing"
}

variable "ai_dubbing_bucket_name" {
  type        = string
  description = "GCS bucket used for deployment tasks"
  default     = "ai_dubbing_bucket"
}

variable "config_spreadsheet_id" {
  type        = string
  description = "The ID of the config spreadhseet"
  default     = "my-spreadhseet-id"
}

variable "execution_schedule" {
  type        = string
  description = "The schedule to execute the process (every 30 min default) "
  default     = "*/30 * * * *"
}

variable "config_sheet_name" {
  type        = string
  description = "The name of the sheet"
  default     = "config"
}

variable "config_sheet_range" {
  type        = string
  description = "Google Cloud Region"
  default     = "config!A1:N"
}

variable "tts_file_column" {
  type        = string
  description = "Column of the TTS file in the config sheet"
  default     = "K"
}

variable "final_video_file_column" {
  type        = string
  description = "Column of the video file in the config sheet"
  default     = "L"
}

variable "status_column" {
  type        = string
  description = "Column for Status in the config sheet"
  default     = "M"
}

variable "last_update_column" {
  type        = string
  description = "Column for last update in the config sheet"
  default     = "N"
}

variable "generate_tts_files_trigger_pubsub_topic" {
  type        = string
  description = "The name for the pubsusb topic to trigger the tts generation cloud function"
  default     = "generate_tts_files_trigger"
}

variable "generate_video_file_trigger_pubsub_topic" {
  type        = string
  description = "The name for the pubsusb topic to trigger the video generation cloud function"
  default     = "generate_video_file_trigger"
}