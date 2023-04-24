## README

# Context

AI Dubbing allows you to create localized videos using the same video base and adding translations using Google AI Powered TextToSpeech API

# Pre-requisites:

*   Google Cloud
*   Google Workspace (Google Spreadsheets)
*   Google Cloud user with privileges over all the APIs listed in the config (ideally Owner role), so it’s possible to grant some privileges to the Service Account automatically. \

*   Latest version of Terraform installed \

*   Python version >= 3.8.1 installed
*   Python Virtualenv installed \


Roles that will be automatically  granted to the service account during the installation process:

"roles/iam.serviceAccountShortTermTokenMinter"

"roles/storage.objectAdmin"

"roles/pubsub.publisher"

# Installation Steps:



1. Open a shell \

2. Clone git repository (GoB only right now:_ git clone "sso://professional-services/solutions/ai\_video\_dubbing_") \

3. Open a text editor and configure the following installation variables in the file _“variables.tf”_

    variable "gcp\_project" {


      type        = string


      description = "Google Cloud Project ID where the artifacts will be deployed"


      default     = "my-project"


    }


    variable "gcp\_region" {


      type        = string


      description = "Google Cloud Region"


      default     = "my-gcp-region"


    }


    variable "ai\_dubbing\_sa" {


      type        = string


      description = "Service Account for the deployment"


      default     = "ai-dubbing"


    }


    variable "ai\_dubbing\_bucket\_name" {


      type        = string


      description = "GCS bucket used for deployment tasks"


      default     = "my-bucket"


    }


    variable "config\_spreadsheet\_id" {


      type        = string


      description = "The ID of the config spreadhseet"


      default     = "my-google-sheets-sheet-id"


    }


    #Do not set this value to a high frequency, since executions might overlap 


    variable "execution\_schedule" {


      type        = string


      description = "The schedule to execute the process (every 30 min default) "


      default     = "\*/30 \* \* \* \*"


    }

4. _Now execute ”terraform apply” \
_
5. Type “yes” and hit return when the system asks for confirmation_ \
_


# Generated Cloud Artifacts



*   Service Account: if it not exists, it will be created as per the values in the configuration
*   Cloud Scheduler: ai-dubbing-trigger
*   Cloud Functions: generate\_tts\_file, generate\_video\_file. Both triggered by pub/sub
*   Cloud Pub/Sub topics: generate\_tts\_files\_trigger, generate\_video\_file\_trigger


# Output

Every generated artifact will be stored in the supplied GCS bucket under the output/YYYYMMDD folder, where YYYY represents the year, MM the month and DD the day of the processing date


## Audio Files

The generated TTS audio files will be stored as mp3

{campaign}-{topic}-{voice\_id}.mp3

Audio url: gs://{gcs\_bucket}/output/{YYYYMMDD}/{campaign}-{topic}-{voice\_id}.mp3


## Video Files

The generated video field will be stored as mp4

{campaign}-{topic}-{voice\_id}.mp4

Video url: gs://{gcs\_bucket}/output/{YYYYMMDD}/{campaign}-{topic}-{voice\_id}.mp4


# 


# How to activate

Most of the effort will be on building the first SSML text and adapting the timings to the video. Once that task is mastered, video creation will be done in a breeze!

You can use the [web-based SSML-Editor](https://actions-on-google-labs.github.io/nightingale-ssml-editor/?%3Cspeak%3E%3Cseq%3E%0A%09%3Cmedia%20xml%3Aid%3D%22track-0%22%20begin%3D%220s%22%20soundLevel%3D%22%2B0dB%22%3E%0A%09%09%3Cspeak%3E%3Cp%3EI%20will%20read%20this%20text%20for%20you%3C%2Fp%3E%3C%2Fspeak%3E%0A%09%3C%2Fmedia%3E%0A%3C%2Fseq%3E%3C%2Fspeak%3E) for this purpose, and then export each SSML file.


## What’s required for video generation



*   A file containing a base video without music
*   A file containing the music for the video


## Configure the input



1. Create a [copy of the configuration spreadsheet](https://docs.google.com/spreadsheets/d/10mWAd_2RQsfyJM1_rgCICLCN_r0QIVAL_z0DzhGNKJg/copy)
2. Configure the fields in the sheet “config” following the instructions

<table>
  <tr>
   <td style="background-color: #34a853">
<strong>Field Name</strong>
   </td>
   <td style="background-color: #34a853"><strong>Type</strong>
   </td>
   <td style="background-color: #34a853"><strong>Description</strong>
   </td>
   <td style="background-color: #34a853"><strong>Sample Value</strong>
   </td>
   <td style="background-color: #34a853"><strong>Notes</strong>
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>campaign</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">A string to generate the name of the video
   </td>
   <td style="background-color: null">summer
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>topic</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">A string to generate the name of the video
   </td>
   <td style="background-color: null">outdoor
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>gcs_bucket</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">The bucket where video_file and base_audio_file could be located (the service account must be granted access). We recommend to use the same gcs_bucket as for the output
   </td>
   <td style="background-color: null">videodub_test_input
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>video_file</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">The location of the master video file within the gcs_bucket
   </td>
   <td style="background-color: null">input/videos/bumper_base_video.mp4
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>base_audio_file</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">The location of the base audio file within the gcs_bucket
   </td>
   <td style="background-color: null">input/audios/bumper_base_audio.mp3
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>text</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">The SSML text to convert to speech
   </td>
   <td style="background-color: null"><speak>
<p>
<par>
<p>
<media soundLevel="+5.5dB">
<p>
<prosody rate="fast" pitch="high">
<p>
Find your own style in the constantly renewed catalog of the &lt;emphasis level="strong">somewhere.com online shop&lt;/emphasis>&lt;/prosody>
<p>
<break time="200ms"/>
<p>
<prosody rate="normal" pitch="high">Design what you love&lt;/prosody>
<p>
</media>
<p>
</par>
<p>
</speak>
   </td>
   <td style="background-color: null"><a href="https://developers.google.com/assistant/conversational/ssml">Check SSML supported syntax</a>
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>voice_id</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">The id of the voice to use
   </td>
   <td style="background-color: null">en-GB-Wavenet-C##FEMALE
   </td>
   <td style="background-color: null">Check voices here
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>millisecond_start_audio</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">Millisecond of the video when the audio must start. This could be also accomplished using TTS
   </td>
   <td style="background-color: null"><p style="text-align: right">
0</p>

   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #4285f4"><strong>audio_encoding</strong>
   </td>
   <td style="background-color: null">Input
   </td>
   <td style="background-color: null">The audio encoding available
   </td>
   <td style="background-color: null">MP3
   </td>
   <td style="background-color: null">At the moment only MP3 is supported
   </td>
  </tr>
  <tr>
   <td style="background-color: #fbbc04"><strong>final_video_file_url</strong>
   </td>
   <td>Output
   </td>
   <td style="background-color: null">The location of the generated video file with the base audio and speech
   </td>
   <td style="background-color: null">gs://videodub_tester/output/20230420/summer-outdoor-en-gb-wavenet-c##female.mp4
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #fbbc04"><strong>status</strong>
   </td>
   <td>Output
   </td>
   <td style="background-color: null">The status of the process
   </td>
   <td style="background-color: null">Video OK
   </td>
   <td style="background-color: null">
   </td>
  </tr>
  <tr>
   <td style="background-color: #fbbc04"><strong>last_update</strong>
   </td>
   <td>Output
   </td>
   <td style="background-color: null">The last time the row was modified by the automatic process
   </td>
   <td style="background-color: null">2023/04/20, 12:25:16
   </td>
   <td style="background-color: null">
   </td>
  </tr>
</table>



## Trigger the generation process

Once all the configuration is set in the spreadsheet, the process will run every X minutes, as defined by the execution\_schedule.

The “Status” column will change its contents, the possible values are:



*   “TTS OK”: audio file generated correctly
*   “Video OK”: video file generated correctly
*   Other value: an error occurred

When all the cells in the status column would display “Video OK”, the process will be completed

When all the cells display “Video OK” or different from “TTS OK”, the process will be completed but it might have errors \


Just download the videos from gs://{gcs\_bucket}/output/{YYYYMMDD} and make the best use of them.

Note

For the initial tests, the scheduled execution period might be too long. The recommendation in these kinds of situations is just to disable the schedule and run it on demand.
