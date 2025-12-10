import pyaudio
import wave
import numpy
import numpy.fft as fft
from scipy.signal import resample_poly
import os

# Global stop condition for the recording thread
stopCondition = False

def StereoToMono(stereoAudio):
    return stereoAudio.mean(axis=1)

def InitialiseAudio(filename):
    """Reads the entire contents of a WAV file."""
    # This function will raise an error if the file is not ready,
    # which will be caught by the calling function.
    with wave.open(filename, 'rb') as sound:
        CHANNELS = sound.getnchannels()
        SAMPLERATE = sound.getframerate()
        n_frames = sound.getnframes()
        
        if n_frames == 0:
            return numpy.array([]), SAMPLERATE

        frames = sound.readframes(n_frames)
        audioData = numpy.frombuffer(frames, dtype=numpy.int16).reshape(-1, CHANNELS)
        return audioData, SAMPLERATE

def GenerateConstellationMap(filename):
    """
    FIX: This function now processes the entire file and is resilient to
    read errors caused by the file being written simultaneously.
    """
    try:
        audioData, SAMPLERATE = InitialiseAudio(filename)
        if audioData.size == 0:
            return numpy.array([])
    except (wave.Error, EOFError, FileNotFoundError):
        # If the file isn't ready, return an empty array. The GUI loop will try again.
        return numpy.array([])

    monoAudio = StereoToMono(audioData)
    
    downsampledAudio = resample_poly(monoAudio, 1, 4)
    SAMPLERATE_NEW = SAMPLERATE // 4
    
    windowSize = 1024
    windowOverlap = 512
    
    if downsampledAudio.shape[0] < windowSize:
        return numpy.array([])
        
    shape = ((downsampledAudio.shape[0] - windowSize) // windowOverlap + 1, windowSize)
    strides = (downsampledAudio.strides[0] * windowOverlap, downsampledAudio.strides[0])
    windowedAudio = numpy.lib.stride_tricks.as_strided(downsampledAudio, shape=shape, strides=strides)
    
    window = numpy.hamming(windowSize)
    windowedAudio = windowedAudio * window
    
    fft_data = fft.fft(windowedAudio, n=windowSize, axis=1)
    fft_data = numpy.abs(fft_data[:, :windowSize // 2])
    
    freq_bands = [0, 10, 20, 40, 80, 160, 511]
    peaks = []
    
    for t_index, time_slice in enumerate(fft_data):
        for i in range(len(freq_bands) - 1):
            start, end = freq_bands[i], freq_bands[i+1]
            band = time_slice[start:end]
            peak_index = numpy.argmax(band) + start
            frequency = peak_index * (SAMPLERATE_NEW / windowSize)
            time_offset = t_index * (windowOverlap / SAMPLERATE_NEW)
            
            if time_slice[peak_index] > 100:
                peaks.append([time_offset, frequency])

    return numpy.array(peaks)

def RecordAudio(recordingDuration, OUTPUT_FILENAME, saveFrequency):
    """
    FIX: This function now writes frames to the file periodically,
    preventing the file from being in an unreadable state.
    """
    global stopCondition
    stopCondition = False
    
    CHANNELS = 1
    SAMPLERATE = 44100
    FORMAT = pyaudio.paInt16
    CHUNK = 1024

    py = pyaudio.PyAudio()
    stream = py.open(channels=CHANNELS, rate=SAMPLERATE, format=FORMAT, input=True, frames_per_buffer=CHUNK)
    
    saveFile = wave.open(OUTPUT_FILENAME, 'wb')
    saveFile.setnchannels(CHANNELS)
    saveFile.setsampwidth(py.get_sample_size(FORMAT))
    saveFile.setframerate(SAMPLERATE)
    
    frames_to_write = []
    total_chunks_to_record = int((SAMPLERATE / CHUNK) * recordingDuration)
    chunks_per_save_interval = int((SAMPLERATE / CHUNK) * saveFrequency)

    try:
        for i in range(total_chunks_to_record):
            if stopCondition:
                break
            
            audioBuffer = stream.read(CHUNK, exception_on_overflow=False)
            frames_to_write.append(audioBuffer)
            
            if len(frames_to_write) >= chunks_per_save_interval:
                saveFile.writeframes(b''.join(frames_to_write))
                frames_to_write.clear()

        if frames_to_write:
            saveFile.writeframes(b''.join(frames_to_write))
    finally:
        stream.stop_stream()
        stream.close()
        py.terminate()
        saveFile.close()
