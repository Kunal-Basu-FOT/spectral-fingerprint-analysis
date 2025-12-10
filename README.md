# Audio Fingerprinting and Music Recognition System

This project is an end-to-end audio fingerprinting engine inspired by Shazam. It aims to identify songs from short audio clips using STFT-based spectrograms, spectral peak constellations, and time-invariant hash generation. The current version is built in Python for rapid prototyping, with a planned migration of performance-critical DSP components to C++ for real-time operation.

---

## Project Overview
- Extracts spectrograms using windowed STFT  
- Detects stable spectral peaks to form constellation maps  
- Generates time–frequency hash pairs robust to noise and time shifts  
- Matches hashed fingerprints for song identification  
- Architecture designed for modular, high-performance scaling  

---

## Current Status
The project is under active development. Core components such as fingerprint generation, hashing logic, and matching pipeline are being implemented and tested in Python. The C++ backend will be introduced once the prototype stabilizes.

---

## Planned Enhancements
- C++ acceleration for DSP operations  
- Improved peak detection and noise robustness  
- Larger and more diverse fingerprint database  
- Faster hash search structures  
- Real-time visualization interface  

---

## Motivation
This project was developed to explore how audio fingerprinting systems work internally and to recreate the core ideas behind large-scale music identification engines using transparent, reproducible methods.

---

## License
MIT License
