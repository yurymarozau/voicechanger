import numpy as np
import struct

from stopwatch import Stopwatch

def get_stopwatch(callback):
	stopwatch = Stopwatch()
	stopwatch.progress_signal.connect(callback)
	return stopwatch

def process_frame(frame):
	frame = struct.unpack(str(2 * len(frame)) + 'B', frame)
	frame = frame[::2]
	frame = np.array(frame, dtype='b') + 128
	return frame

def fft_vectorized(frame):
	frame = np.asarray(frame, dtype=float)
	N = frame.shape[0]

	N_min = min(N, 32)
	
	n = np.arange(N_min)
	k = n[:, None]
	M = np.exp(-2j * np.pi * n * k / N_min)
	X = np.dot(M, frame.reshape((N_min, -1)))

	while X.shape[0] < N:
		X_even = X[:, :int(X.shape[1] / 2)]
		X_odd = X[:, int(X.shape[1] / 2):]
		factor = np.exp(-1j * np.pi * np.arange(X.shape[0]) / X.shape[0])[:, None]
		X = np.vstack([X_even + factor * X_odd,
					   X_even - factor * X_odd])

	return X.ravel()

def ifft(frame):
	return np.fft.ifft(frame)

def transform_frame_for_spectrum(frame):
	phi_s = []
	frame = fft_vectorized(frame)
	frame = frame[:int(len(frame) / 2)]
	phi_s = [compl.imag / compl.real for compl in frame]
	amplitudes = abs(frame)
	return amplitudes, phi_s

def transform_frame_for_spectrogram(frame, chunk_size, win, image_array):
	amplitudes, phi_s = transform_frame_for_spectrum(frame * win)
	amplitudes /= chunk_size
	amplitudes = 10 * np.log10(amplitudes)

	image_array = np.roll(image_array, -1, 0)
	image_array[-1:] = amplitudes
	return image_array