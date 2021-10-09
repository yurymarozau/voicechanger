import numpy as np
import struct

from stopwatch import Stopwatch

def sin_taylor(x):
	eps = 0.0000001
	
	n = 1
	curr_value = x
	sum_ = 0
	
	while abs(curr_value) > eps:
		sum_ += curr_value
		curr_value *= -(x * x) / ((n + 1) * (n + 2))
		n += 2
	
	return sum_

def calc_harmonic_signal(A, N, n, phi, f):
	arg = (((2 * np.pi * f * n) / N) + phi)
	if arg >= 2 * np.pi:
		arg -= 2 * np.pi * (arg // (2 * np.pi))
	return A * sin_taylor(arg)

def calc_polyharmonic_signal(A_s, chunk_size, phi_s, f_s):
	N = chunk_size
	
	data_x = np.arange(0, N)

	data_y = np.zeros((N,), dtype=int)
	for i, A in enumerate(A_s):
		data_y = np.add(data_y, [calc_harmonic_signal(A, N, point_x, phi_s[i], f_s[i]) for point_x in data_x])

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