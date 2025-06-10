# Pycord modules
import discord
from discord.sinks import Sink, PCMSink

# Other modules
import asyncio
from typing import List


class DataStreamer:
    def __init__(self, voice: discord.VoiceClient, clip_size: int = 30, chunk_size: int = 1):
        self.audio_data_buffer: List[dict] = []
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

        sink_processed = asyncio.Event()

        async def callback(sink: Sink):
            if not self.is_streaming:  # stop() was called
                return

            current_chunk = sink.audio_data

            # Flush oldest chunk and add new chunk
            if len(self.audio_data_buffer) * self.chunk_size > self.clip_size:
                self.audio_data_buffer.pop(0)
            self.audio_data_buffer.append(current_chunk)

            sink_processed.set()
            sink_processed.clear()

        async def stream_loop():
            self.is_streaming = True
            while True:
                sink = PCMSink()

                self.voice.start_recording(sink, callback)
                await asyncio.sleep(self.chunk_size)
                self.voice.stop_recording()

                await sink_processed.wait()

        self.stream_loop_task = asyncio.get_event_loop().create_task(stream_loop())

    def stop(self) -> None:
        """Stop streaming audio data into buffers"""
        if not self.is_streaming:
            raise Exception("Can't stop DataStreamer if not already streaming")

        self.is_streaming = False
        self.voice.stop_recording()
        self.stream_loop_task.cancel()
