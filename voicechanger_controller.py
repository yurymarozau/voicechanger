from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot

import sys

import pyqtgraph

import numpy as np

import utils

from voicechanger_view import Ui_form_voicechanger
from micro_recorder import MicroRecorder
from input_thread import InputThread
from output_thread import OutputThread


class VoiceChangerController(QtCore.QObject):
	def __init__(self):
		super().__init__()
		self.__init_params()
		self.__init_ui_form()
		self.__init_scenes()
		self.__init_plot_wdgs()

	def __init_params(self):
		self.__canvas_width_default = 600
		self.__canvas_height_default = 275

		self.__canvas_width_input = self.__canvas_width_default
		self.__canvas_height_input = self.__canvas_height_default

		self.__canvas_width_spectrogram = self.__canvas_width_default
		self.__canvas_height_spectrogram = self.__canvas_height_default

		self.__canvas_width_spectrum = self.__canvas_width_default
		self.__canvas_height_spectrum = self.__canvas_height_default

		self.__canvas_width_output = self.__canvas_width_default
		self.__canvas_height_output = self.__canvas_height_default

		self.__rate = 44100
		self.__chunk_size = 2048

		self.__x_range = {
			'start': 0,
			'end': self.__chunk_size,
		}

		self.__y_range = {
			'start': 0,
			'end': 255,
		}

		self.__x_range_spectrogram = {
			'start': 0, 
			'end': 100,
		}

		self.__y_range_spectrogram = {
			'start': 0, 
			'end': 50000,
		}

		self.__x_range_spectrum = {
			'start': 0,
			'end': self.__chunk_size / 2,
		}

		self.__y_range_spectrum = {
			'start': 0,
			'end': 50000,
		}

		self.__record_frames = []
		self.__record_frames_fft = []
		self.__is_recording = False

		self.__frequency_slider_range_min = -100
		self.__frequency_slider_range_max = 100
		self.__frequency_slider_single_step = 1
		self.__frequency_slider_coeff = 10
		self.__frequency_slider_start_value = 10

	def __init_ui_form(self):
		self.app = QtWidgets.QApplication(sys.argv)
		self.form = QtWidgets.QMainWindow()
		self.ui = Ui_form_voicechanger()
		self.ui.setupUi(self.form)

	def __init_scenes(self):
		self.__scene_input = self.__init_scene(
			self.ui.gv_visualizer_input, 
			self.__canvas_width_input, 
			self.__canvas_height_input
		)
		self.__scene_spectrogram = self.__init_scene(
			self.ui.gv_spectrogram, 
			self.__canvas_width_spectrogram, 
			self.__canvas_height_spectrogram
		)
		self.__scene_spectrum = self.__init_scene(
			self.ui.gv_spectrum, 
			self.__canvas_width_spectrum, 
			self.__canvas_height_spectrum
		)
		self.__scene_output = self.__init_scene(
			self.ui.gv_visualizer_output, 
			self.__canvas_width_output, 
			self.__canvas_height_output
		)

	def __init_plot_wdgs(self):
		self.__plot_wdg_input, self.__plot_item_input = self.__init_plot_wdg(
			scene=self.__scene_input, 
			x_range=self.__x_range, 
			y_range=self.__y_range, 
			width=self.__canvas_width_input, 
			height=self.__canvas_height_input
		)
		self.__plot_wdg_spectrogram, self.__plot_item_spectrogram = self.__init_plot_wdg(
			scene=self.__scene_spectrogram, 
			width=self.__canvas_width_spectrogram, 
			height=self.__canvas_height_spectrogram
		)
		self.__spectrogram, self.__spectrogram_bar, self.__image_array, self.__win = self.__init_spectrogram_image(self.__plot_wdg_spectrogram, self.__plot_item_spectrogram)

		self.__plot_wdg_spectrum, self.__plot_item_spectrum = self.__init_plot_wdg(
			scene=self.__scene_spectrum, 
			x_range=self.__x_range_spectrum, 
			y_range=self.__y_range_spectrum, 
			width=self.__canvas_width_spectrum, 
			height=self.__canvas_height_spectrum
		)

		self.__plot_wdg_output, self.__plot_item_output = self.__init_plot_wdg(
			scene=self.__scene_output, 
			x_range=self.__x_range, 
			y_range=self.__y_range, 
			width=self.__canvas_width_output, 
			height=self.__canvas_height_output
		)

	def __init_frequency_slider(self):
		self.ui.hs_frequency.setRange(self.__frequency_slider_range_min, self.__frequency_slider_range_max)
		self.ui.hs_frequency.setSingleStep(self.__frequency_slider_single_step)
		self.ui.hs_frequency.valueChanged.connect(self.__change_frequency_slider_coeff)
		self.ui.hs_frequency.setValue(self.__frequency_slider_start_value)

	def __init_scene(self, graphics_view, width, height):
		graphics_view.setFixedSize(width, height)
		scene = QtWidgets.QGraphicsScene()
		scene.setSceneRect(0, 0, width, height)
		graphics_view.setScene(scene)
		return scene

	def __init_plot_wdg(
			self, 
			scene=None, 
			x_range=None, 
			y_range=None, 
			width=100, 
			height=100
		):

		plot_wdg = pyqtgraph.PlotWidget()
		plot_wdg.resize(width, height)
		plot_item = plot_wdg.getPlotItem()
		if x_range:
			plot_item.setXRange(x_range['start'], x_range['end'], padding=0.005)
		if y_range:
			plot_item.setYRange(y_range['start'], y_range['end'])
		if scene:
			scene.addWidget(plot_wdg)
		return plot_wdg, plot_item

	def __init_spectrogram_image(self, plot_wdg, plot_item):
		image_array = np.zeros((int(self.__chunk_size / 2), int(self.__chunk_size / 2)))

		image = pyqtgraph.ImageItem(image=image_array)
		plot_wdg.addItem(image)

		freqs = np.arange((self.__chunk_size / 2) + 1) / (self.__chunk_size / self.__rate)
		scale_y = 1 / (image_array.shape[1] / freqs[-1])

		tr = QtGui.QTransform() 
		tr.scale((1 / self.__rate) * self.__chunk_size, scale_y)   
		image.setTransform(tr)

		cm = pyqtgraph.colormap.get('CET-L9')
		bar = pyqtgraph.ColorBarItem(cmap=cm)
		bar.setImageItem(image, insert_in=plot_item)
		bar.setLevels((np.min(freqs), np.max(freqs)))

		plot_wdg.setLabel('left', 'Frequency', units='Hz')

		win = np.hanning(self.__chunk_size)

		return image, bar, image_array, win


	def start(self):	
		self.ui.pb_record.clicked.connect(self.__pb_record_click)
		self.ui.pb_play.clicked.connect(self.__pb_play_click)
		self.ui.pb_play_recovered.clicked.connect(self.__pb_play_recovered_click)

		self.__micro = self.__handle_micro()

		self.__micro_thread = self.__get_micro_thread(
			micro=self.__micro, 
			recv_signal_handler=self.__handle_new_frames, 
			error_signal_handler=self.__msgbox_message
		)

		self.__micro.start_input_stream()
		self.__start_thread(self.__micro_thread)

		self.__output_thread = self.__get_output_thread(
			micro=self.__micro,
			progress_signal_handler=lambda frame: self.__output_frame_to_plot(self.__plot_item_output, frame),
			complete_signal_handler=lambda: self.__pb_stop_click(self.__stop_play),
			error_signal_handler=self.__msgbox_message
		)

		self.__init_frequency_slider()

		self.__stopwatch = utils.get_stopwatch(
			lambda minutes, seconds, milliseconds: 
			self.ui.lb_record_time.setText('{}:{}:{}'.format(minutes, seconds, milliseconds))
		)

		self.__update_form()
		sys.exit(self.app.exec_())

	def __pb_stop_click(self, callback):
		self.ui.pb_stop.setEnabled(False)
		callback()

	def __pb_record_click(self):
		self.__record_frames = []
		self.__record_frames_fft = []
		self.__is_recording = True

		self.ui.pb_play.setEnabled(False)

		self.ui.pb_record.setEnabled(False)

		self.ui.pb_stop.clicked.connect(lambda: self.__pb_stop_click(self.__stop_record))
		self.ui.pb_stop.setEnabled(True)

		self.__stopwatch.start()

	def __stop_record(self):
		self.__stopwatch.stop()

		self.__is_recording = False

		self.__quit_thread(self.__micro_thread)

		for i, frame in enumerate(self.__record_frames):
			new_recovered_frame = utils.fft_vectorized(frame)
			new_recovered_frame = utils.ifft(new_recovered_frame).real.astype('int16')
			self.__record_frames_fft.append(new_recovered_frame)

		self.ui.pb_record.setEnabled(True)
		self.ui.pb_play.setEnabled(True)
		self.ui.pb_play_recovered.setEnabled(True)

	def __pb_play_click(self):
		self.ui.pb_record.setEnabled(False)
		self.ui.pb_play.setEnabled(False)
		self.ui.pb_play_recovered.setEnabled(False)
		self.ui.pb_stop.clicked.connect(lambda: self.__pb_stop_click(self.__stop_play))
		self.ui.pb_stop.setEnabled(True)
		self.__micro.start_output_stream()
		self.__play_record()

	def __stop_play(self):
		self.__quit_thread(self.__output_thread)
		self.ui.pb_play.setEnabled(True)
		self.ui.pb_play_recovered.setEnabled(True)
		self.__micro.stop_output_stream()
		self.ui.pb_record.setEnabled(True)

	def __pb_play_recovered_click(self):
		self.ui.pb_record.setEnabled(False)
		self.ui.pb_play.setEnabled(False)
		self.ui.pb_play_recovered.setEnabled(False)
		self.ui.pb_stop.clicked.connect(lambda: self.__pb_stop_click(self.__stop_play_recovered))
		self.ui.pb_stop.setEnabled(True)
		self.__micro.start_output_stream()
		self.__play_recovered_record()

	def __stop_play_recovered(self):
		self.__quit_thread(self.__output_thread)
		self.ui.pb_play.setEnabled(True)
		self.ui.pb_play_recovered.setEnabled(True)
		self.__micro.stop_output_stream()
		self.ui.pb_record.setEnabled(True)

	def __play_record(self):
		self.__output_thread.set_frames(self.__record_frames)
		self.__start_thread(self.__output_thread)

	def __play_recovered_record(self):
		self.__output_thread.set_frames(self.__record_frames_fft)
		self.__start_thread(self.__output_thread)

	def __handle_micro(self):
		micro = MicroRecorder(rate=self.__rate, chunk_size=self.__chunk_size)
		return micro

	def __get_micro_thread(self, micro=None, recv_signal_handler=None, error_signal_handler=None):
		micro_thread = InputThread(micro)
		if recv_signal_handler:
			micro_thread.recv_signal.connect(recv_signal_handler)
		if error_signal_handler:
			micro_thread.error_signal.connect(error_signal_handler)
		return micro_thread

	def __start_thread(self, thread):
		thread.start()
		thread.wait(1)

	def __quit_thread(self, thread):
		thread.quit()

	def __get_output_thread(self, micro=None, progress_signal_handler=None, complete_signal_handler=None, error_signal_handler=None):
		output_thread = OutputThread(micro)
		if progress_signal_handler:
			output_thread.progress_signal.connect(progress_signal_handler)
		if complete_signal_handler:
			output_thread.complete_signal.connect(complete_signal_handler)
		if error_signal_handler:
			output_thread.error_signal.connect(error_signal_handler)
		return output_thread

	def __change_frequency_slider_coeff(self, value):
		self.ui.le_frequency.setText('{:.1f}'.format(value / self.__frequency_slider_coeff))
		self.__output_thread.set_frequency_coeff(value / self.__frequency_slider_coeff)

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

			self.__output_frame_to_plot_spectrogram(self.__spectrogram, self.__spectrogram_bar, input_last_frame)

			self.__output_frame_to_plot_spectrum(self.__plot_item_spectrum, input_last_frame)

	def __output_frame_to_plot(self, plot_item, frame, color='w'):
		plot_item.clear()
		frame = utils.process_frame(frame)
		plot_item.setXRange(self.__x_range['start'], len(frame))
		plot_item.plot(width=3, y=frame, pen=color)

	def __output_frame_to_plot_spectrogram(self, image, bar, frame):
		self.__image_array = utils.transform_frame_for_spectrogram(frame, self.__chunk_size, self.__win, self.__image_array)
		image.setImage(self.__image_array)

	def __output_frame_to_plot_spectrum(self, plot_item, frame, color='w'):
		plot_item.clear()
		amplitudes, phi_s = utils.transform_frame_for_spectrum(frame)
		plot_item.plot(width=3, y=amplitudes, pen=color)

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


