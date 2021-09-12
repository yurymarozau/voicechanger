from PyQt5.QtCore import QThread, pyqtSignal

import time


class InputThread(QThread):
	recv_signal = pyqtSignal(list)
	error_signal = pyqtSignal(str, str)

	def __init__(self, micro=None):
		super().__init__()
		self.__micro = micro

	def run(self):
		if self.__micro:
			while True:
				frames = self.__micro.get_frames()
				if frames:
					self.recv_signal.emit(frames)
				time.sleep(0)

	def __send_error_message(self, title, message):
		self.error_signal.emit(title, message)



