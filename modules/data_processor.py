# Clipped modules
from models.member import ClippedMember
from modules.data_streamer import DataStreamer

# Pycord modules
import discord
import discord.opus as op
import discord.sinks as sinks

# Other modules
import io
import pydub
from typing import Dict, List
import wave


class DataProcessor:
    def __init__(self,
                 voice: discord.VoiceClient,
                 streamer: DataStreamer):
        self.vc = voice
        """Client of voice channel that this audio data is coming from"""
        self.streamer = streamer
        """DataStreamer object whose audio data we're processing"""
        self.clip_size = streamer.clip_size
        """The size of a clip, in seconds"""
        self.chunk_size = streamer.chunk_size
        """Size of audio chunks in buffer, in seconds"""

        # WAV header parameters
        self.channels = op.Decoder.CHANNELS
        self.sampling_width = op.Decoder.SAMPLE_SIZE // self.channels
        self.sampling_rate = op.Decoder.SAMPLING_RATE

    def process_audio_data(self) -> io.BytesIO:
        """
        Transforms raw AudioData chunks from Pycord into a "clip",
        outputted in WAV format.
        """

        # This outlines the outputs of each step within this
        # audio data processing pipeline
        filtered_data: List[Dict[discord.Member, sinks.AudioData]]
        wav_chunks: List[Dict[discord.Member, io.BytesIO]]
        standardized_wav_chunks: List[Dict[discord.Member, pydub.AudioSegment]]
        overlayed_wav_chunks: List[pydub.AudioSegment]
        clip: pydub.AudioSegment

        # These actually carry out the series of steps in the pipeline
        filtered_data = self._filter_opted_in_members()
        wav_chunks = self._prepend_wav_headers(filtered_data)
        standardized_wav_chunks = self._standardize_chunk_sizes(wav_chunks)
        overlayed_wav_chunks = self._overlay_member_audios(
            standardized_wav_chunks)
        clip = self._concatenate_chunks(overlayed_wav_chunks, overlay=True)

        # Return final clip as BytesIO object
        clip_bytes_io = io.BytesIO()
        clip.export(clip_bytes_io, format="wav")
        clip_bytes_io.seek(0)

        return clip_bytes_io

    def process_audio_data_by_member(self):
        """
        Transforms raw AudioData chunks from Pycord into a list of 
        synced, equal-length WAV clips for each member that spoke. 
        This function is primarily used so per-member transcription
        can be offloaded elsewhere.
        """

        # This outlines the outputs of each step within this
        # audio data processing pipeline
        filtered_data: List[Dict[discord.Member, sinks.AudioData]]
        wav_chunks: List[Dict[discord.Member, io.BytesIO]]
        standardized_wav_chunks: List[Dict[discord.Member, pydub.AudioSegment]]
        clip_by_member: Dict[discord.Member, pydub.AudioSegment]

        # These actually carry out the series of the steps in the pipeline.
        # It's pretty much the same as process_audio_data(), but we skip
        # the step of overlaying all members' audio.
        filtered_data = self._filter_opted_in_members()
        wav_chunks = self._prepend_wav_headers(filtered_data)
        standardized_wav_chunks = self._standardize_chunk_sizes(wav_chunks)
        clip_by_member = self._concatenate_chunks(
            standardized_wav_chunks, overlay=False)

        # Convert users' AudioSegments to BytesIO for more flexibility downstream
        clip_by_member_bytes: Dict[discord.Member, io.BytesIO] = {}
        for user, audio in clip_by_member.items():
            audio_bytes = io.BytesIO()
            audio.export(audio_bytes, format="wav")
            audio_bytes.seek(0)
            clip_by_member_bytes[user] = audio_bytes

        return clip_by_member_bytes

    def _filter_opted_in_members(self):
        """Filter for 'opted-in' users"""
        opted_in = {member.id: member
                    for member
                    in ClippedMember.get_opted_in_members(self.vc.channel.members)}
        filtered_data: List[Dict[discord.Member, sinks.AudioData]] = []
        for chunk in self.streamer.audio_data_buffer:
            filtered_chunk = {opted_in[member_id]: data
                              for member_id, data in chunk.items()
                              if member_id in opted_in.keys()}
            filtered_data.append(filtered_chunk)

        return filtered_data

    def _prepend_wav_headers(self, filtered_data):
        """
        Convert all users' audio data within each chunk to 
        WAV format by prepending WAV headers.
        """
        wav_chunks: List[Dict[discord.Member, io.BytesIO]] = []
        for chunk in filtered_data:
            wav_chunk: Dict[discord.Member, io.BytesIO] = {}
            for member, member_audio_data in chunk.items():
                member_wav = io.BytesIO()
                with wave.open(member_wav, "wb") as w:
                    # write WAV headers
                    w.setnchannels(self.channels)
                    w.setsampwidth(self.sampling_width)
                    w.setframerate(self.sampling_rate)
                    # write the actual audio data
                    w.writeframes(member_audio_data.file.getvalue())
                member_wav.seek(0)
                wav_chunk[member] = member_wav
            wav_chunks.append(wav_chunk)

        return wav_chunks

    def _standardize_chunk_sizes(self, wav_chunks):
        """
        Left-pad audio chunks with appropriate amount of silence so that
        they are all synced and equal sized. This prepares the audio 
        chunks for each member to be accurately overlayed.
        """
        standardized_wav_chunks: List[Dict[discord.Member, pydub.AudioSegment]]
        standardized_wav_chunks = []
        for chunk in wav_chunks:
            standardized_wav_chunk = {}
            for member, member_audio_data in chunk.items():
                segment: pydub.AudioSegment = (pydub.AudioSegment
                                               .from_file(member_audio_data,
                                                          format="wav"))

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

                standardized_wav_chunk[member] = padded_segment

            standardized_wav_chunks.append(standardized_wav_chunk)

        return standardized_wav_chunks

    def _overlay_member_audios(self, standardized_wav_chunks):
        """Overlay all users' audio for each WAV audio chunk"""
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

        return overlayed_wav_chunks

    def _concatenate_chunks(self, wav_chunks, overlay=True):
        """
        Concatenate WAV audio chunks into single clip. If the given
        WAV chunks are an overlay of members, then this function will
        output a pydub.AudioSegment. Otherwise, if it's not an overlay
        (i.e. WAV chunks are still separated by user), then this function
        will return a dictionary, mapping each user to their own 
        concatenated pydub.AudioSegment.
        """
        clip = None
        if overlay:
            clip: pydub.AudioSegment = (pydub.AudioSegment
                                        .silent(duration=0)
                                        .set_channels(self.channels)
                                        .set_sample_width(self.sampling_width)
                                        .set_frame_rate(self.sampling_rate))

            for chunk in wav_chunks:
                if not isinstance(chunk, pydub.AudioSegment):
                    raise Exception("Chunks within wav_chunks should be of type pydub.AudioSegment "
                                    "if wav_chunks is an overlay of all members' audio. "
                                    f"Instead got chunks of type '{type(chunk)}'")

                clip += chunk
        else:
            clip: Dict[discord.Member, pydub.AudioSegment] = {}

            for chunk in wav_chunks:
                if not isinstance(chunk, Dict):
                    raise Exception("Chunks within wav_chunks should be of type Dict if wav_chunks "
                                    "is not an overlay (i.e. audio data is separated by member). "
                                    f"Instead got chunks of type '{type(chunk)}'")

                for member, new_member_chunk in chunk.items():
                    member_audio_segment = clip.get(member)
                    if member_audio_segment is None:
                        member_audio_segment = (pydub.AudioSegment
                                                .silent(duration=0)
                                                .set_channels(self.channels)
                                                .set_sample_width(self.sampling_width)
                                                .set_frame_rate(self.sampling_rate))
                    clip[member] = member_audio_segment + new_member_chunk

        return clip
