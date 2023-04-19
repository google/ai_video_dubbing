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

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

data "google_project" "project" {
  provider = google
}

resource "google_service_account" "service_account" {
  account_id   = var.ai_dubbing_sa
  display_name = "AI Dubbing Service Account"
}

resource "google_project_service" "enable_cloudbuild" {
  project = var.gcp_project
  service = "cloudbuild.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on    = [google_service_account.service_account]
}

resource "google_project_service" "enable_texttospeech_api" {
  project = var.gcp_project
  service = "texttospeech.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on    = [google_service_account.service_account]
}

resource "google_project_service" "enable_sheetsapi" {
  project = var.gcp_project
  service = "sheets.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on    = [google_service_account.service_account]
}

resource "google_project_service" "enable_cloudfunctions" {
  project = var.gcp_project
  service = "cloudfunctions.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on    = [google_service_account.service_account]
}

resource "google_project_service" "enable_pubsub" {
  project = var.gcp_project
  service = "pubsub.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on    = [google_service_account.service_account]
}

resource "google_project_service" "enable_cloudscheduler" {
  project = var.gcp_project
  service = "cloudscheduler.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on    = [google_service_account.service_account]
}

resource "google_project_iam_member" "permissions_token" {
  project = data.google_project.project.project_id
  role   = "roles/iam.serviceAccountShortTermTokenMinter"
  member = "serviceAccount:${google_service_account.service_account.email}"
  depends_on    = [google_service_account.service_account]
}

resource "google_project_iam_member" "permissions_gcs" {
  project = data.google_project.project.project_id
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.service_account.email}"
  depends_on    = [google_service_account.service_account]
}

resource "google_project_iam_member" "permissions_pubsub" {
  project = data.google_project.project.project_id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.service_account.email}"
  depends_on    = [google_service_account.service_account]
}

resource "google_pubsub_topic" "generate_tts_files_trigger_topic" {
  depends_on    = [google_project_service.enable_pubsub]
  name = var.generate_tts_files_trigger_pubsub_topic
}

resource "google_pubsub_topic" "generate_video_file_trigger_topic" {
  depends_on    = [google_project_service.enable_pubsub]
  name = var.generate_video_file_trigger_pubsub_topic
}

resource "google_cloud_scheduler_job" "job" {
  depends_on    = [google_pubsub_topic.generate_tts_files_trigger_topic]
  name        = "ai-dubbing-trigger"
  description = "ai-dubbing-trigger"
  schedule    = "*/5 * * * *"

  pubsub_target {
    topic_name = google_pubsub_topic.generate_tts_files_trigger_topic.id
    data       = base64encode("None")
  }
}