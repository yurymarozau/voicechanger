from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot

import sys

import pyqtgraph

import numpy as np
import struct

from voicechanger_view import Ui_form_voicechanger
from micro_recorder import MicroRecorder
from input_thread import InputThread
from output_thread import OutputThread


class VoiceChangerController(QtCore.QObject):
	def __init__(self):
		super().__init__()
		self.__init_params()
		self.__init_ui_form()
		self.__init_scene_input()
		self.__init_scene_output()

	def __init_params(self):
		self.__rate = 44100
		self.__chunk_coeff = 20
		# self.__chunk_size = int(self.__rate / self.__chunk_coeff)
		self.__chunk_size = 2048

		self.__record_frames = []
		self.__is_recording = False

	def __init_ui_form(self):
		self.app = QtWidgets.QApplication(sys.argv)
		self.form = QtWidgets.QMainWindow()
		self.ui = Ui_form_voicechanger()
		self.ui.setupUi(self.form)

	def __init_scene_input(self):
		self.__canvas_width = 980
		self.__canvas_height = 275
		self.ui.gv_visualizer_input.setFixedSize(self.__canvas_width, self.__canvas_height)

		self.__scene_input = QtWidgets.QGraphicsScene()
		self.__scene_input.setSceneRect(0, 0, self.__canvas_width, self.__canvas_height)

		self.ui.gv_visualizer_input.setScene(self.__scene_input)

	def __init_scene_output(self):
		self.__canvas_width = 980
		self.__canvas_height = 275
		self.ui.gv_visualizer_output.setFixedSize(self.__canvas_width, self.__canvas_height)

		self.__scene_output = QtWidgets.QGraphicsScene()
		self.__scene_output.setSceneRect(0, 0, self.__canvas_width, self.__canvas_height)

		self.ui.gv_visualizer_output.setScene(self.__scene_output)

	def __init_plot_wdg(self, scene, x_range, y_range, width, height):
		plot_wdg = pyqtgraph.PlotWidget()
		plot_wdg.resize(width, height)
		plot_item = plot_wdg.getPlotItem()
		plot_item.setYRange(y_range['start'], y_range['end'])
		plot_item.setXRange(x_range['start'], x_range['end'], padding=0.005)
		scene.addWidget(plot_wdg)
		return plot_wdg, plot_item

	def start(self):
		x_range = {
			'start': 0,
			'end': self.__chunk_size,
		}
		y_range = {
			'start': 0,
			'end': 255,
		}
		self.__plot_wdg_input, self.__plot_item_input = self.__init_plot_wdg(
			self.__scene_input, 
			x_range, 
			y_range, 
			self.__canvas_width, 
			self.__canvas_height
		)
		self.__plot_wdg_output, self.__plot_item_output = self.__init_plot_wdg(
			self.__scene_output, 
			x_range, 
			y_range, 
			self.__canvas_width, 
			self.__canvas_height
		)
		self.ui.pb_record.clicked.connect(self.__pb_record_click)
		self.ui.pb_play.clicked.connect(self.__pb_play_click)

		self.__micro = self.__handle_micro()
		
		# self.__timer = self.__start_timer()

		self.__micro_thread = self.__get_micro_thread(
			micro=self.__micro, 
			recv_signal_handler=self.__handle_new_frames, 
			error_signal_handler=self.__msgbox_message
		)

		self.__micro.start_input_stream()
		self.__start_micro_thread(self.__micro_thread)

		self.__output_thread = self.__get_output_thread(
			micro=self.__micro,
			progress_signal_handler=lambda frame: self.__output_frame_to_plot(self.__plot_item_output, frame),
			complete_signal_handler=lambda: self.__pb_stop_click(self.__stop_play),
			error_signal_handler=self.__msgbox_message
		)

		self.__update_form()
		sys.exit(self.app.exec_())

	def __pb_stop_click(self, callback):
		self.ui.pb_stop.setEnabled(False)
		callback()

	def __pb_record_click(self):
		self.__record_frames = []
		self.__is_recording = True
		self.ui.pb_play.setEnabled(False)
		self.ui.pb_record.setEnabled(False)
		self.ui.pb_stop.clicked.connect(lambda: self.__pb_stop_click(self.__stop_record))
		self.ui.pb_stop.setEnabled(True)

	def __stop_record(self):
		self.__is_recording = False
		self.__quit_micro_thread(self.__micro_thread)
		self.ui.pb_record.setEnabled(True)
		self.ui.pb_play.setEnabled(True)

	def __pb_play_click(self):
		self.ui.pb_record.setEnabled(False)
		self.ui.pb_play.setEnabled(False)
		self.ui.pb_stop.clicked.connect(lambda: self.__pb_stop_click(self.__stop_play))
		self.__micro.start_output_stream()
		self.__play_record()

	def __stop_play(self):
		self.__quit_output_thread(self.__output_thread)
		self.ui.pb_play.setEnabled(True)
		self.__micro.stop_output_stream()
		self.ui.pb_record.setEnabled(True)

	def __play_record(self):
		self.__output_thread.set_frames(self.__record_frames)
		self.__start_output_thread(self.__output_thread)

	def __handle_micro(self):
		micro = MicroRecorder(rate=self.__rate, chunk_size=self.__chunk_size)
		return micro

	def __start_timer(self):
		timer = QtCore.QTimer()
		# timer.timeout.connect(self.__handle_new_frames)
		# timer.start(1)

		return timer

	def __get_micro_thread(self, micro=None, recv_signal_handler=None, error_signal_handler=None):
		micro_thread = InputThread(micro)
		if recv_signal_handler:
			micro_thread.recv_signal.connect(recv_signal_handler)
		if error_signal_handler:
			micro_thread.error_signal.connect(error_signal_handler)
		return micro_thread

	def __start_micro_thread(self, micro_thread):
		micro_thread.start()
		micro_thread.wait(1)

	def __quit_micro_thread(self, micro_thread):
		micro_thread.quit()

	def __get_output_thread(self, micro=None, progress_signal_handler=None, complete_signal_handler=None, error_signal_handler=None):
		output_thread = OutputThread(micro)
		if progress_signal_handler:
			output_thread.progress_signal.connect(progress_signal_handler)
		if complete_signal_handler:
			output_thread.complete_signal.connect(complete_signal_handler)
		if error_signal_handler:
			output_thread.error_signal.connect(error_signal_handler)
		return output_thread

	def __start_output_thread(self, output_thread):
		output_thread.start()
		output_thread.wait(1)

	def __quit_output_thread(self, output_thread):
		output_thread.quit()

	@pyqtSlot(list)
	def __handle_new_frames(self, frames):
		color = 'w'
		if frames:
			last_frame = frames[-1]
			input_last_frame = last_frame.copy()

			if self.__is_recording:
				self.__record_frames += frames
				color = 'c'

			self.__output_frame_to_plot(self.__plot_item_input, input_last_frame, color=color)

			# output_last_frame = input_last_frame.copy()
			# self.__output_frame_to_plot(self.__plot_item_output, output_last_frame)

	def __process_frame(self, frame):
		frame = struct.unpack(str(2 * self.__chunk_size) + 'B', frame)
		frame = frame[::2]
		frame = np.array(frame, dtype='b') + 128
		return frame

	def __output_frame_to_plot(self, plot_item, frame, color='w'):
		plot_item.clear()

		frame = self.__process_frame(frame)

		plot_item.plot(width=3, y=frame, pen=color)

	def __update_form(self):
		self.form.hide()
		self.form.show()

	def __msgbox_message(self, title, message):
		msgBox = QtWidgets.QMessageBox()
		msgBox.setText(title)
		msgBox.setInformativeText(
			message
		)
		msgBox.exec_()


if __name__ == '__main__':
	voicechanger_controller = VoiceChangerController()
	voicechanger_controller.start()


