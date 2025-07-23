# Clipped modules
from bw_secrets import CLIPS_METADATA_COLLECTION, TRANSCRIPTION_MODEL
import modules.database as db

# Pycord modules
import discord

# Other modules
from datetime import datetime
import io
import openai
from typing import Dict


class Clip:
    def __init__(self,
                 guild: discord.Guild,
                 timestamp: datetime,
                 clip_by_member: Dict[discord.Member, io.BytesIO],
                 bucket_location: str):
        self.ai_client = openai.OpenAI()

        self.guild = guild
        self.timestamp = timestamp
        self.clip_by_member = clip_by_member
        self.bucket_location = bucket_location

        self.transcription = None
        self.transcription_summary = None
        self.summary_embedding = None

    def create_clip_metadata_in_db(self):
        self.transcription = self._generate_transcription()
        self.transcription_summary = self._generate_transcription_summary()
        self.summary_embedding = self._generate_summary_embedding()

        # Fields of database document
        self.fields = {
            "_id": {"guild_id": self.guild.id, "timestamp": self.timestamp},
            "transcription": self.transcription,
            "summary": self.transcription_summary,
            "summary_embedding": self.summary_embedding,
            "bucket_location": self.bucket_location
        }

        db.create_document(collection_name=CLIPS_METADATA_COLLECTION,
                           obj=self.fields)

    def _generate_transcription(self) -> str:
        segments_with_speaker = []

        for member, audio_bytes in self.clip_by_member.items():
            audio_bytes.name = f"{member.id}-audio.wav"

            # Transcribe with timestamps
            transcript = self.ai_client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=audio_bytes,
                response_format="verbose_json"
            )

            # Transcription timestamped by segment,
            transcript_json = transcript.model_dump()
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

    def _generate_summary_embedding(self):
        if self.transcription_summary is None:
            raise Exception("Transcription summary hasn't been generated yet. "
                            "Call _generate_transcription_summary() first")
