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

		self.__frequency_coeff = 1

		self.__frames = []

	def run(self):
		if self.__micro:
			for frame in self.__frames:
				frame = self.__change_frequency(frame)
				self.__play_frame(frame)
				self.progress_signal.emit(frame)

		self.complete_signal.emit()

	def set_frames(self, frames):
		self.__frames = frames

	def set_frequency_coeff(self, coeff):
		self.__frequency_coeff = coeff

	def __play_frame(self, frame):
		self.__micro.write_frame(frame.tobytes())

	def __change_frequency(self, frame):
		new_frame = []
		new_indicies = []

		for ind, item in enumerate(frame):
			new_indicies.append(ind * self.__frequency_coeff)

		new_indicies = np.asarray(new_indicies)
		new_indicies = np.rint(new_indicies).astype(int)

		for ind in new_indicies:
			if ind >= len(frame):
				break
			new_frame.append(frame[ind])

		new_frame = np.asarray(new_frame)
		return new_frame

	def __send_error_message(self, title, message):
		self.error_signal.emit(title, message)



