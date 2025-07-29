# Pycord modules
import discord
import discord.opus as op
from discord.sinks import Sink, PCMSink

# Other modules
import asyncio
from typing import Deque


class DataStreamer:
    def __init__(self,
                 voice: discord.VoiceClient,
                 clip_size: int = 30,
                 chunk_size: int = 1):
        self.audio_data_buffer: Deque[dict] = Deque(
            maxlen=int(clip_size / chunk_size) + 1)
        """Buffer of audio data, straight from Pycord"""
        self.voice = voice
        """Voice client we're streaming audio from"""
        self.is_streaming = False
        """Indicates whether or not we're actively capturing audio"""
        self.clip_size = clip_size
        """Size of clips in seconds"""
        self.chunk_size = chunk_size
        """Size of audio chunks in buffer, in seconds"""
        self.stream_loop_task = None
        """Task that's running the loop to stream voice data from Discord"""

    async def start(self) -> None:
        """Begin streaming audio data into buffers"""
        if self.is_streaming:
            return

        async def noop_callback(sink: Sink):
            pass

        async def stream_loop():
            sink = PCMSink()
            self.is_streaming = True
            self.voice.start_recording(sink, noop_callback)

            while True:
                await asyncio.sleep(self.chunk_size)

                # sink.audio_data.

        self.stream_loop_task = (asyncio
                                 .get_event_loop()
                                 .create_task(stream_loop()))

    def stop(self) -> None:
        """Stop streaming audio data into buffers"""
        if not self.is_streaming:
            raise Exception("Can't stop DataStreamer if not already streaming")

        self.is_streaming = False

        if self.voice.recording:
            self.voice.stop_recording()

        self.stream_loop_task.cancel()

    @staticmethod
    def bytes_to_seconds(num_bytes: int) -> float:
        """Utility function to calculate seconds of audio, given length of bytes."""
        sampling_rate = op.Decoder.SAMPLING_RATE
        sample_size = op.Decoder.SAMPLE_SIZE

        duration = num_bytes / (sampling_rate * sample_size)

        return duration

    @staticmethod
    def seconds_to_bytes(duration: float) -> int:
        """Utility function to calculate number of bytes, given seconds of audio."""
        sampling_rate = op.Decoder.SAMPLING_RATE
        sample_size = op.Decoder.SAMPLE_SIZE

        num_bytes = int(duration * sampling_rate * sample_size)
        print(f"\n\n{num_bytes}\n\n")

        return num_bytes
