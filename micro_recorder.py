import pyaudio
import threading
import atexit
import numpy as np


class MicroRecorder(object):
	def __init__(self, format_=pyaudio.paInt16, channels=1, rate=44100, chunk_size=2048):
		self.__format = format_
		self.__channels = channels
		self.__rate = rate
		self.__chunk_size = chunk_size

		self.__frames = []

		self.__lock = threading.Lock()
		self.__stop = False

		atexit.register(self.__close)

		self.__p_input, self.__stream_input = self.__init_pyaudio_input()
		self.__p_output, self.__stream_output = self.__init_pyaudio_output()

	def __init_pyaudio_input(self):
		self.__p_input = pyaudio.PyAudio()
		self.__stream_input = self.__p_input.open(
			format=self.__format,
			channels=self.__channels,
			rate=self.__rate,
			input=True,
			frames_per_buffer=self.__chunk_size,
			stream_callback=self.recv_frame_callback
		)
		return self.__p_input, self.__stream_input

	def __init_pyaudio_output(self):
		self.__p_output = pyaudio.PyAudio()
		self.__stream_output = self.__p_output.open(
			format=self.__format,
			channels=self.__channels,
			rate=self.__rate,
			output=True
		)
		return self.__p_output, self.__stream_output

	def recv_frame_callback(self, data, frame_count, time_info, status):
		data = np.fromstring(data, 'int16')
		with self.__lock:
			self.__frames.append(data)
			if self.__stop:
				return None, pyaudio.paComplete
		return data, pyaudio.paContinue
	
	def get_frames(self):
		with self.__lock:
			frames = self.__frames
			self.__frames = []
			return frames
	
	def write_frame(self, frame):
		self.__stream_output.write(frame)

	def start(self):
		self.start_input_stream()
		self.start_output_stream()

	def stop(self):
		self.stop_input_stream()
		self.stop_output_stream()

	def start_input_stream(self):
		self.__stream_input.start_stream()

	def stop_input_stream(self):
		self.__stream_input.stop_stream()

	def start_output_stream(self):
		self.__stream_output.start_stream()

	def stop_output_stream(self):
		self.__stream_output.stop_stream()

	def __close(self):
		with self.__lock:
			self.__stop = True
		self.__stream_input.close()
		self.__stream_output.close()
		self.__p_input.terminate()
		self.__p_output.terminate()
