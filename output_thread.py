from PyQt5.QtCore import QThread, pyqtSignal

import time
import numpy as np


class OutputThread(QThread):
	progress_signal = pyqtSignal(np.ndarray)
	complete_signal = pyqtSignal()
	error_signal = pyqtSignal(str, str)

	def __init__(self, micro=None):
		super().__init__()
		self.__micro = micro
		self.__frames = []

	def run(self):
		if self.__micro:
			for frame in self.__frames:
				self.__play_frame(frame.tobytes())
				self.progress_signal.emit(frame)

		self.complete_signal.emit()

	def set_frames(self, frames):
		self.__frames = frames

	def __play_frame(self, frame):
		self.__micro.write_frame(frame)

	def __send_error_message(self, title, message):
		self.error_signal.emit(title, message)



