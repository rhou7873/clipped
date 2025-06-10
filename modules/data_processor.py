# Clipped modules
from modules.data_streamer import DataStreamer
import modules.database as db

# Pycord modules
import discord
import discord.sinks as sinks

# Other modules
import io
import pydub
from typing import Dict, List
import wave


class DataProcessor:
    def __init__(self, voice_client: discord.VoiceClient, streamer: DataStreamer):
        self.vc = voice_client
        """Client of voice channel that this audio data is coming from"""
        self.streamer = streamer
        """DataStreamer object whose audio data we're processing"""
        self.clip_size = streamer.clip_size
        """The size of a clip, in seconds"""
        self.chunk_size = streamer.chunk_size
        """Size of audio chunks in buffer, in seconds"""

        # WAV header parameters
        self.channels = self.vc.decoder.CHANNELS
        self.sampling_width = self.vc.decoder.SAMPLE_SIZE // self.channels
        self.sampling_rate = self.vc.decoder.SAMPLING_RATE

    async def process_audio_data(self) -> io.BytesIO:
        """
        Transforms raw AudioData chunks from Pycord into a "clip", outputted in WAV format.
        """

        # Filter for "opted-in" users
        opted_in = [member.id
                    for member in db.get_opted_in_members(self.vc.channel.members)]
        filtered_data: List[Dict[int, sinks.AudioData]] = []
        for chunk in self.streamer.audio_data_buffer:
            filtered_chunk = {user_id: data
                              for user_id, data in chunk.items()
                              if user_id in opted_in}
            filtered_data.append(filtered_chunk)

        # Convert all users' audio data within each chunk to WAV format
        # by prepending WAV headers
        wav_chunks: List[Dict[int, io.BytesIO]] = []
        for chunk in filtered_data:
            wav_chunk: Dict[int, io.BytesIO] = {}
            for user_id, user_audio_data in chunk.items():
                user_wav = io.BytesIO()
                with wave.open(user_wav, "wb") as w:
                    # write WAV headers
                    w.setnchannels(self.channels)
                    w.setsampwidth(self.sampling_width)
                    w.setframerate(self.sampling_rate)
                    # write the actual audio data
                    w.writeframes(user_audio_data.file.getvalue())
                user_wav.seek(0)
                wav_chunk[user_id] = user_wav
            wav_chunks.append(wav_chunk)

        # Standardize audio chunk sizes
        standardized_wav_chunks: List[Dict[int, pydub.AudioSegment]] = []
        for chunk in wav_chunks:
            standardized_wav_chunk = {}
            for user_id, user_audio_data in chunk.items():
                segment: pydub.AudioSegment = (pydub.AudioSegment
                                               .from_file(user_audio_data, format="wav"))

                # compute left padding needed
                eps = 50
                segment_size_ms = int(segment.duration_seconds * 1000)
                target_size_ms = int(self.chunk_size * 1000)
                padding_size_ms = target_size_ms - segment_size_ms

                if padding_size_ms < -eps:
                    raise Exception(
                        "Length of audio chunk for a user shouldn't be longer "
                        f"than chunk size, segment_size_ms={segment_size_ms}, "
                        f"target_size_ms={target_size_ms}")

                # generate silence
                silence = (pydub.AudioSegment
                           .silent(duration=max(padding_size_ms, 0))
                           .set_channels(self.channels)
                           .set_sample_width(self.sampling_width)
                           .set_frame_rate(self.sampling_rate))

                # prepend silence
                padded_segment = silence + segment

                standardized_wav_chunk[user_id] = padded_segment

            standardized_wav_chunks.append(standardized_wav_chunk)

        # Overlay all users' audio for each WAV audio chunk
        overlayed_wav_chunks: List[pydub.AudioSegment] = []
        for chunk in standardized_wav_chunks:
            # initialize base with a silent chunk
            overlayed_wav_chunk = (pydub.AudioSegment
                                   .silent(duration=self.chunk_size * 1000)
                                   .set_channels(self.channels)
                                   .set_sample_width(self.sampling_width)
                                   .set_frame_rate(self.sampling_rate))

            # iteratively overlay all the users' voices
            for _, user_audio_data in chunk.items():
                overlayed_wav_chunk = (overlayed_wav_chunk
                                       .overlay(user_audio_data))

            overlayed_wav_chunks.append(overlayed_wav_chunk)

        # Concatenate WAV audio chunks into single clip
        clip: pydub.AudioSegment = (pydub.AudioSegment
                                    .silent(duration=0)
                                    .set_channels(self.channels)
                                    .set_sample_width(self.sampling_width)
                                    .set_frame_rate(self.sampling_rate))
        for chunk in overlayed_wav_chunks:
            clip += chunk

        # Return final clip as BytesIO object
        clip_bytes_io = io.BytesIO()
        clip.export(clip_bytes_io, format="wav")
        clip_bytes_io.seek(0)
        return clip_bytes_io
