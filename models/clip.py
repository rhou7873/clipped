# Clipped modules
from bw_secrets import (CLIPS_METADATA_COLLECTION,
                        EMBEDDING_MODEL,
                        SUMMARY_MODEL,
                        SUMMARY_SYSTEM_PROMPT,
                        TRANSCRIPTION_MODEL)
import modules.database as db

# Pycord modules
import discord

# Other modules
from datetime import datetime
from google.cloud import storage
import io
import openai
from typing import Dict
import uuid


class Clip:
    def __init__(self, guild: discord.Guild):
        self.ai_client = openai.OpenAI()

        self.guild = guild
        self.timestamp = datetime.now()
        self.timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        self.transcription = None
        self.transcription_summary = None
        self.summary_embedding = None

    def store_clip_in_blob(self, clip_bytes: io.BytesIO) -> str:
        # Generate a unique filename
        clip_id = str(uuid.uuid4())
        file_name = f"{self.guild.name}-{self.guild.id}-{clip_id}.wav"

        # Ensure BytesIO buffer pointer is at the beginning
        clip_bytes.seek(0)

        # Initialize GCS client and bucket
        client = storage.Client()
        BUCKET_NAME = "clipped"
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)

        # Upload the audio clip
        blob.upload_from_file(clip_bytes, content_type="audio/wav")

        return f"gs://{BUCKET_NAME}/{file_name}"

    def store_clip_metadata_in_db(self,
                                  clip_by_member: Dict[discord.Member, io.BytesIO],
                                  object_uri: str):
        self.transcription = self._generate_transcription(clip_by_member)
        self.transcription_summary = self._generate_transcription_summary()
        self.summary_embedding = self._generate_summary_embedding()

        # Fields of database document
        self.fields = {
            "_id": {"guild_id": self.guild.id, "timestamp": self.timestamp},
            "transcription": self.transcription,
            "summary": self.transcription_summary,
            "summary_embedding": self.summary_embedding,
            "uri": object_uri
        }

        db.create_document(collection_name=CLIPS_METADATA_COLLECTION,
                           obj=self.fields)

    def _generate_transcription(self, clip_by_member: Dict[discord.Member, io.BytesIO]) -> str:
        segments_with_speaker = []

        for member, audio_bytes in clip_by_member.items():
            audio_bytes.name = f"{member.id}-audio.wav"

            # Transcribe with timestamps
            transcription_response = self.ai_client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=audio_bytes,
                response_format="verbose_json"
            )

            # Transcription timestamped by segment,
            transcript_json = transcription_response.model_dump()
            for seg in transcript_json["segments"]:
                segments_with_speaker.append({
                    "member_name": member.name,
                    "start": seg["start"],
                    "text": seg["text"].strip()
                })

        # Sort all segments by start time
        ordered_segments = sorted(
            segments_with_speaker, key=lambda s: s["start"])

        # Format output with speaker labels
        full_transcript = []
        for seg in ordered_segments:
            tag = f"[{seg['member_name']}]"
            full_transcript.append(f"{tag}: {seg['text']}")

        return "\n".join(full_transcript)

    def _generate_transcription_summary(self) -> str:
        if self.transcription is None:
            raise Exception("Transcription hasn't been generated yet. "
                            "Call _generate_transcription() first")

        input = SUMMARY_SYSTEM_PROMPT + self.transcription
        summary_response = self.ai_client.responses.create(model=SUMMARY_MODEL,
                                                           input=input)
        return summary_response.output[0].content[0].text

    def _generate_summary_embedding(self):
        if self.transcription_summary is None:
            raise Exception("Transcription summary hasn't been generated yet. "
                            "Call _generate_transcription_summary() first")

        embedding_response = self.ai_client.embeddings.create(model=EMBEDDING_MODEL,
                                                              input=self.transcription_summary)
        return embedding_response.data[0].embedding
