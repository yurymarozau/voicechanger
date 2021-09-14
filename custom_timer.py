from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class CustomTimer(QObject):
	progress_signal = pyqtSignal(int, int, int)
	error_signal = pyqtSignal(str, str)

	def __init__(self):
		super().__init__()
		self.__timeout_value = 1
		
		self.__counter = 0

		self.__timer = QTimer()
		self.__timer.timeout.connect(self.__tick)

	def start(self):
		self.__timer.start(self.__timeout_value)

	def stop(self):
		self.__timer.stop()
		self.reset_counter()

	def reset_counter(self):
		self.__counter = 0

	def __tick(self):
		self.__counter += 1
		minutes, seconds, milliseconds = self.__count_time()
		self.progress_signal.emit(minutes, seconds, milliseconds)

	def __count_time(self):
		milliseconds = self.__counter
		minutes = (milliseconds // 1000) // 60
		milliseconds -= minutes * 1000 * 60
		seconds = milliseconds // 1000
		milliseconds -= seconds * 1000
		return minutes, seconds, milliseconds


	def __send_error_message(self, title, message):
		self.error_signal.emit(title, message)



