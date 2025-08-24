#!/usr/bin/env python3
"""Продвинутые методы сегментации аудио для распознавания речи"""

import os
import json
import numpy as np
import librosa
import librosa.display
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import entropy
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from pathlib import Path
import logging

class AdvancedSegmentation:
    """Продвинутые методы сегментации аудио"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Параметры по умолчанию
        self.default_config = {
            'INTONATION_WINDOW_SIZE': 50,      # мс
            'EMOTION_ANALYSIS_ENABLED': True,
            'ENERGY_PATTERN_ENABLED': True,
            'CONTEXT_AWARE_ENABLED': True,
            'MIN_SEGMENT_DURATION': 3000,      # мс
            'MAX_SEGMENT_DURATION': 60000,     # мс
            'ENERGY_THRESHOLD': 0.1,
            'INTONATION_SENSITIVITY': 0.8,
            'EMOTION_CLUSTERS': 3,
            'SAVE_VISUALIZATIONS': True
        }
        
        # Обновляем конфигурацию
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
    
    def segment_by_intonation_patterns(self, audio_path: str) -> list:
        """Сегментация по паттернам интонации и тона"""
        try:
            self.logger.info("Начинаю сегментацию по интонационным паттернам...")
            
            # Загружаем аудио
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Извлекаем характеристики интонации
            pitch, voiced_flag, voiced_probs = librosa.pyin(
                y, 
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr,
                frame_length=2048,
                hop_length=512
            )
            
            # Извлекаем MFCC для анализа тембра
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=512)
            
            # Анализируем изменения интонации
            pitch_changes = self._detect_pitch_changes(pitch, voiced_flag)
            timbre_changes = self._detect_timbre_changes(mfcc)
            
            # Комбинируем изменения
            all_changes = self._combine_changes(pitch_changes, timbre_changes)
            
            # Создаем сегменты
            segments = self._create_intonation_segments(y, sr, all_changes)
            
            # Сохраняем визуализацию
            if self.config['SAVE_VISUALIZATIONS']:
                self._save_intonation_visualization(audio_path, pitch, mfcc, all_changes, segments)
            
            self.logger.info(f"Создано {len(segments)} сегментов по интонации")
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка интонационной сегментации: {e}")
            return []
    
    def segment_by_emotional_patterns(self, audio_path: str) -> list:
        """Сегментация по эмоциональным паттернам речи"""
        try:
            self.logger.info("Начинаю сегментацию по эмоциональным паттернам...")
            
            # Загружаем аудио
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Извлекаем эмоциональные характеристики
            spectral_features = self._extract_emotional_features(y, sr)
            
            # Кластеризуем по эмоциональным паттернам
            emotion_clusters = self._cluster_emotional_patterns(spectral_features)
            
            # Определяем границы эмоциональных изменений
            emotion_changes = self._detect_emotion_changes(emotion_clusters)
            
            # Создаем сегменты
            segments = self._create_emotion_segments(y, sr, emotion_changes)
            
            # Сохраняем визуализацию
            if self.config['SAVE_VISUALIZATIONS']:
                self._save_emotion_visualization(audio_path, spectral_features, emotion_clusters, segments)
            
            self.logger.info(f"Создано {len(segments)} сегментов по эмоциям")
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка эмоциональной сегментации: {e}")
            return []
    
    def segment_by_energy_patterns(self, audio_path: str) -> list:
        """Сегментация по энергетическим паттернам речи"""
        try:
            self.logger.info("Начинаю сегментацию по энергетическим паттернам...")
            
            # Загружаем аудио
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Извлекаем энергетические характеристики
            energy = librosa.feature.rms(y=y, hop_length=512)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y, hop_length=512)[0]
            
            # Анализируем энергетические паттерны
            energy_patterns = self._analyze_energy_patterns(energy, zero_crossing_rate)
            
            # Определяем границы энергетических изменений
            energy_changes = self._detect_energy_changes(energy_patterns)
            
            # Создаем сегменты
            segments = self._create_energy_segments(y, sr, energy_changes)
            
            # Сохраняем визуализацию
            if self.config['SAVE_VISUALIZATIONS']:
                self._save_energy_visualization(audio_path, energy, zero_crossing_rate, energy_changes, segments)
            
            self.logger.info(f"Создано {len(segments)} сегментов по энергии")
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка энергетической сегментации: {e}")
            return []
    
    def segment_by_context_awareness(self, audio_path: str) -> list:
        """Адаптивная сегментация на основе контекста"""
        try:
            self.logger.info("Начинаю контекстно-адаптивную сегментацию...")
            
            # Загружаем аудио
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Анализируем контекст речи
            context_features = self._analyze_speech_context(y, sr)
            
            # Адаптивно настраиваем параметры сегментации
            adaptive_params = self._adapt_segmentation_params(context_features)
            
            # Применяем адаптивную сегментацию
            segments = self._apply_adaptive_segmentation(y, sr, adaptive_params)
            
            self.logger.info(f"Создано {len(segments)} адаптивных сегментов")
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка адаптивной сегментации: {e}")
            return []
    
    def _detect_pitch_changes(self, pitch: np.ndarray, voiced_flag: np.ndarray) -> list:
        """Определение изменений высоты тона"""
        try:
            # Фильтруем только озвученные фрагменты
            voiced_pitch = pitch[voiced_flag]
            voiced_times = np.where(voiced_flag)[0]
            
            if len(voiced_pitch) < 2:
                return []
            
            # Вычисляем изменения высоты тона
            pitch_diffs = np.diff(voiced_pitch)
            
            # Нормализуем изменения
            pitch_diffs_norm = (pitch_diffs - np.mean(pitch_diffs)) / (np.std(pitch_diffs) + 1e-8)
            
            # Находим значительные изменения
            threshold = self.config['INTONATION_SENSITIVITY']
            change_indices = np.where(np.abs(pitch_diffs_norm) > threshold)[0]
            
            # Конвертируем в временные метки
            change_times = [int(voiced_times[i] * 512 / 16000 * 1000) for i in change_indices]
            
            return change_times
            
        except Exception as e:
            self.logger.error(f"Ошибка определения изменений высоты тона: {e}")
            return []
    
    def _detect_timbre_changes(self, mfcc: np.ndarray) -> list:
        """Определение изменений тембра"""
        try:
            # Вычисляем изменения MFCC между соседними фреймами
            mfcc_diffs = np.diff(mfcc, axis=1)
            
            # Вычисляем евклидово расстояние для каждого изменения
            distances = np.linalg.norm(mfcc_diffs, axis=0)
            
            # Сглаживаем сигнал
            smoothed_distances = savgol_filter(distances, window_length=5, polyorder=2)
            
            # Находим пики изменений
            threshold = np.mean(smoothed_distances) + 0.5 * np.std(smoothed_distances)
            change_indices = find_peaks(smoothed_distances, height=threshold, distance=10)[0]
            
            # Конвертируем в миллисекунды
            change_times = [int(i * 512 / 16000 * 1000) for i in change_indices]
            
            return change_times
            
        except Exception as e:
            self.logger.error(f"Ошибка определения изменений тембра: {e}")
            return []
    
    def _combine_changes(self, pitch_changes: list, timbre_changes: list) -> list:
        """Объединение изменений от разных методов"""
        try:
            # Объединяем все изменения
            all_changes = pitch_changes + timbre_changes
            all_changes.sort()
            
            # Убираем близкие изменения (в пределах 500мс)
            filtered_changes = []
            for change in all_changes:
                if not filtered_changes or change - filtered_changes[-1] > 500:
                    filtered_changes.append(change)
            
            return filtered_changes
            
        except Exception as e:
            self.logger.error(f"Ошибка объединения изменений: {e}")
            return []
    
    def _extract_emotional_features(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Извлечение эмоциональных характеристик"""
        try:
            # Извлекаем спектральные характеристики
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=512)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=512)[0]
            spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=512)[0]
            
            # Извлекаем ритмические характеристики
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
            beat_features = librosa.feature.tempogram(y=y, sr=sr, hop_length=512)
            
            # Проверяем размеры и приводим к одинаковой длине
            min_length = min(
                len(spectral_centroid), 
                len(spectral_rolloff), 
                len(spectral_bandwidth),
                spectral_contrast.shape[1],
                beat_features.shape[1]
            )
            
            # Обрезаем все признаки до одинаковой длины
            spectral_centroid = spectral_centroid[:min_length]
            spectral_rolloff = spectral_rolloff[:min_length]
            spectral_bandwidth = spectral_bandwidth[:min_length]
            spectral_contrast = spectral_contrast[:, :min_length]
            beat_features = beat_features[:, :min_length]
            
            # Комбинируем все признаки
            features = np.vstack([
                spectral_centroid, 
                spectral_rolloff, 
                spectral_bandwidth,
                np.mean(spectral_contrast, axis=0),
                np.mean(beat_features, axis=0)
            ])
            
            return features
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения эмоциональных признаков: {e}")
            return np.array([])
    
    def _cluster_emotional_patterns(self, features: np.ndarray) -> np.ndarray:
        """Кластеризация эмоциональных паттернов"""
        try:
            if features.size == 0:
                return np.array([])
            
            # Транспонируем для правильной формы
            features_t = features.T
            
            # Нормализуем признаки
            scaler = StandardScaler()
            features_normalized = scaler.fit_transform(features_t)
            
            # Кластеризуем
            n_clusters = min(self.config['EMOTION_CLUSTERS'], len(features_normalized))
            if n_clusters < 2:
                return np.zeros(len(features_normalized))
            
            clustering = DBSCAN(eps=0.5, min_samples=5).fit(features_normalized)
            
            return clustering.labels_
            
        except Exception as e:
            self.logger.error(f"Ошибка кластеризации эмоций: {e}")
            return np.array([])
    
    def _detect_emotion_changes(self, emotion_clusters: np.ndarray) -> list:
        """Определение изменений эмоций"""
        try:
            if emotion_clusters.size == 0:
                return []
            
            # Находим границы между кластерами
            cluster_changes = np.diff(emotion_clusters)
            change_indices = np.where(cluster_changes != 0)[0]
            
            # Конвертируем в миллисекунды
            change_times = [int(i * 512 / 16000 * 1000) for i in change_indices]
            
            return change_times
            
        except Exception as e:
            self.logger.error(f"Ошибка определения изменений эмоций: {e}")
            return []
    
    def _analyze_energy_patterns(self, energy: np.ndarray, zero_crossing_rate: np.ndarray) -> dict:
        """Анализ энергетических паттернов"""
        try:
            # Нормализуем энергию
            energy_norm = (energy - np.min(energy)) / (np.max(energy) - np.min(energy) + 1e-8)
            
            # Анализируем паттерны
            patterns = {
                'energy_levels': energy_norm,
                'energy_variance': np.var(energy_norm),
                'energy_peaks': find_peaks(energy_norm, height=0.7, distance=10)[0],
                'zero_crossing_rate': zero_crossing_rate,
                'speech_activity': energy_norm > self.config['ENERGY_THRESHOLD']
            }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа энергетических паттернов: {e}")
            return {}
    
    def _detect_energy_changes(self, energy_patterns: dict) -> list:
        """Определение энергетических изменений"""
        try:
            if not energy_patterns:
                return []
            
            energy_levels = energy_patterns.get('energy_levels', [])
            if len(energy_levels) < 2:
                return []
            
            # Находим изменения энергии
            energy_diffs = np.diff(energy_levels)
            
            # Находим значительные изменения
            threshold = np.std(energy_diffs) * 1.5
            change_indices = np.where(np.abs(energy_diffs) > threshold)[0]
            
            # Конвертируем в миллисекунды
            change_times = [int(i * 512 / 16000 * 1000) for i in change_indices]
            
            return change_times
            
        except Exception as e:
            self.logger.error(f"Ошибка определения энергетических изменений: {e}")
            return []
    
    def _create_intonation_segments(self, y: np.ndarray, sr: int, change_points: list) -> list:
        """Создание сегментов на основе интонации"""
        try:
            segments = []
            change_points = sorted(change_points)
            
            # Добавляем начало и конец
            if not change_points or change_points[0] > 5000:
                change_points.insert(0, 0)
            
            total_duration = len(y) / sr * 1000
            if not change_points or change_points[-1] < total_duration - 5000:
                change_points.append(int(total_duration))
            
            # Создаем сегменты
            for i in range(len(change_points)):
                start_time = change_points[i]
                
                if i + 1 < len(change_points):
                    end_time = change_points[i + 1]
                else:
                    end_time = int(total_duration)
                
                duration = end_time - start_time
                
                # Проверяем минимальную длительность
                if duration >= self.config['MIN_SEGMENT_DURATION']:
                    start_sample = int(start_time / 1000 * sr)
                    end_sample = int(end_time / 1000 * sr)
                    
                    if start_sample < len(y) and end_sample <= len(y):
                        segment_audio = y[start_sample:end_sample]
                        
                        segments.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': duration,
                            'audio': segment_audio,
                            'start_sample': start_sample,
                            'end_sample': end_sample,
                            'segmentation_method': 'intonation'
                        })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка создания интонационных сегментов: {e}")
            return []
    
    def _create_emotion_segments(self, y: np.ndarray, sr: int, change_points: list) -> list:
        """Создание сегментов на основе эмоций"""
        try:
            segments = []
            change_points = sorted(change_points)
            
            # Добавляем начало и конец
            if not change_points or change_points[0] > 5000:
                change_points.insert(0, 0)
            
            total_duration = len(y) / sr * 1000
            if not change_points or change_points[-1] < total_duration - 5000:
                change_points.append(int(total_duration))
            
            # Создаем сегменты
            for i in range(len(change_points)):
                start_time = change_points[i]
                
                if i + 1 < len(change_points):
                    end_time = change_points[i + 1]
                else:
                    end_time = int(total_duration)
                
                duration = end_time - start_time
                
                # Проверяем минимальную длительность
                if duration >= self.config['MIN_SEGMENT_DURATION']:
                    start_sample = int(start_time / 1000 * sr)
                    end_sample = int(end_time / 1000 * sr)
                    
                    if start_sample < len(y) and end_sample <= len(y):
                        segment_audio = y[start_sample:end_sample]
                        
                        segments.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': duration,
                            'audio': segment_audio,
                            'start_sample': start_sample,
                            'end_sample': end_sample,
                            'segmentation_method': 'emotion'
                        })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка создания эмоциональных сегментов: {e}")
            return []
    
    def _create_energy_segments(self, y: np.ndarray, sr: int, change_points: list) -> list:
        """Создание сегментов на основе энергии"""
        try:
            segments = []
            change_points = sorted(change_points)
            
            # Добавляем начало и конец
            if not change_points or change_points[0] > 5000:
                change_points.insert(0, 0)
            
            total_duration = len(y) / sr * 1000
            if not change_points or change_points[-1] < total_duration - 5000:
                change_points.append(int(total_duration))
            
            # Создаем сегменты
            for i in range(len(change_points)):
                start_time = change_points[i]
                
                if i + 1 < len(change_points):
                    end_time = change_points[i + 1]
                else:
                    end_time = int(total_duration)
                
                duration = end_time - start_time
                
                # Проверяем минимальную длительность
                if duration >= self.config['MIN_SEGMENT_DURATION']:
                    start_sample = int(start_time / 1000 * sr)
                    end_sample = int(end_time / 1000 * sr)
                    
                    if start_sample < len(y) and end_sample <= len(y):
                        segment_audio = y[start_sample:end_sample]
                        
                        segments.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': duration,
                            'audio': segment_audio,
                            'start_sample': start_sample,
                            'end_sample': end_sample,
                            'segmentation_method': 'energy'
                        })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка создания энергетических сегментов: {e}")
            return []
    
    def _analyze_speech_context(self, y: np.ndarray, sr: int) -> dict:
        """Анализ контекста речи"""
        try:
            # Анализируем общие характеристики
            duration = len(y) / sr
            energy = np.mean(librosa.feature.rms(y=y, hop_length=512))
            
            # Определяем тип речи
            if duration < 30:  # Короткая речь
                speech_type = 'short'
                min_segment = 1000  # 1 секунда
                max_segment = 10000  # 10 секунд
            elif duration < 300:  # Средняя речь
                speech_type = 'medium'
                min_segment = 3000  # 3 секунды
                max_segment = 30000  # 30 секунд
            else:  # Длинная речь
                speech_type = 'long'
                min_segment = 5000  # 5 секунд
                max_segment = 60000  # 60 секунд
            
            # Анализируем качество аудио
            noise_level = np.std(y)
            if noise_level > 0.1:
                quality = 'noisy'
                sensitivity_multiplier = 1.5
            else:
                quality = 'clean'
                sensitivity_multiplier = 1.0
            
            context = {
                'speech_type': speech_type,
                'duration': duration,
                'energy_level': energy,
                'noise_level': noise_level,
                'quality': quality,
                'min_segment_duration': min_segment,
                'max_segment_duration': max_segment,
                'sensitivity_multiplier': sensitivity_multiplier
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа контекста речи: {e}")
            return {}
    
    def _adapt_segmentation_params(self, context: dict) -> dict:
        """Адаптация параметров сегментации"""
        try:
            if not context:
                return self.default_config
            
            # Адаптируем параметры на основе контекста
            adapted_params = self.config.copy()
            
            # Адаптируем длительность сегментов
            adapted_params['MIN_SEGMENT_DURATION'] = context.get('min_segment_duration', 3000)
            adapted_params['MAX_SEGMENT_DURATION'] = context.get('max_segment_duration', 60000)
            
            # Адаптируем чувствительность
            sensitivity_multiplier = context.get('sensitivity_multiplier', 1.0)
            adapted_params['INTONATION_SENSITIVITY'] *= sensitivity_multiplier
            adapted_params['ENERGY_THRESHOLD'] *= sensitivity_multiplier
            
            # Адаптируем количество кластеров эмоций
            if context.get('speech_type') == 'short':
                adapted_params['EMOTION_CLUSTERS'] = 2
            elif context.get('speech_type') == 'long':
                adapted_params['EMOTION_CLUSTERS'] = 4
            else:
                adapted_params['EMOTION_CLUSTERS'] = 3
            
            return adapted_params
            
        except Exception as e:
            self.logger.error(f"Ошибка адаптации параметров: {e}")
            return self.config
    
    def _apply_adaptive_segmentation(self, y: np.ndarray, sr: int, params: dict) -> list:
        """Применение адаптивной сегментации"""
        try:
            # Временно обновляем конфигурацию
            original_config = self.config.copy()
            self.config.update(params)
            
            # Применяем комбинированную сегментацию
            segments = []
            
            # Интонационная сегментация
            if params.get('INTONATION_ANALYSIS_ENABLED', True):
                pitch_changes = self._detect_pitch_changes(
                    librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr=sr)[0],
                    librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr=sr)[1]
                )
                intonation_segments = self._create_intonation_segments(y, sr, pitch_changes)
                segments.extend(intonation_segments)
            
            # Эмоциональная сегментация
            if params.get('EMOTION_ANALYSIS_ENABLED', True):
                emotion_features = self._extract_emotional_features(y, sr)
                emotion_clusters = self._cluster_emotional_patterns(emotion_features)
                emotion_changes = self._detect_emotion_changes(emotion_clusters)
                emotion_segments = self._create_emotion_segments(y, sr, emotion_changes)
                segments.extend(emotion_segments)
            
            # Энергетическая сегментация
            if params.get('ENERGY_PATTERN_ENABLED', True):
                energy = librosa.feature.rms(y=y, hop_length=512)[0]
                zero_crossing_rate = librosa.feature.zero_crossing_rate(y, hop_length=512)[0]
                energy_patterns = self._analyze_energy_patterns(energy, zero_crossing_rate)
                energy_changes = self._detect_energy_changes(energy_patterns)
                energy_segments = self._create_energy_segments(y, sr, energy_changes)
                segments.extend(energy_segments)
            
            # Восстанавливаем оригинальную конфигурацию
            self.config = original_config
            
            # Убираем дубликаты и сортируем
            unique_segments = self._remove_duplicate_segments(segments)
            unique_segments.sort(key=lambda x: x['start_time'])
            
            return unique_segments
            
        except Exception as e:
            self.logger.error(f"Ошибка адаптивной сегментации: {e}")
            return []
    
    def _remove_duplicate_segments(self, segments: list) -> list:
        """Удаление дублирующихся сегментов"""
        try:
            if not segments:
                return []
            
            unique_segments = []
            for segment in segments:
                is_duplicate = False
                for existing in unique_segments:
                    # Проверяем перекрытие более чем на 50%
                    overlap_start = max(segment['start_time'], existing['start_time'])
                    overlap_end = min(segment['end_time'], existing['end_time'])
                    overlap_duration = max(0, overlap_end - overlap_start)
                    
                    segment_duration = segment['end_time'] - segment['start_time']
                    existing_duration = existing['end_time'] - existing['start_time']
                    
                    if overlap_duration > 0.5 * min(segment_duration, existing_duration):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_segments.append(segment)
            
            return unique_segments
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления дубликатов: {e}")
            return segments
    
    def _save_intonation_visualization(self, audio_path: str, pitch: np.ndarray, mfcc: np.ndarray, change_points: list, segments: list):
        """Сохранение визуализации интонационной сегментации"""
        try:
            # Создаем папку для визуализаций
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            viz_dir = Path(f"data/audio_processing/{base_name}_visualizations")
            viz_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем график
            fig, axes = plt.subplots(3, 1, figsize=(15, 10))
            
            # График высоты тона
            times = np.arange(len(pitch)) * 512 / 16000
            axes[0].plot(times, pitch)
            axes[0].set_title('Высота тона (Pitch)')
            axes[0].set_ylabel('Частота (Гц)')
            
            # Отмечаем точки изменения
            for change in change_points:
                change_time = change / 1000
                axes[0].axvline(x=change_time, color='red', alpha=0.7, linestyle='--')
            
            # График MFCC
            axes[1].imshow(mfcc, aspect='auto', origin='lower')
            axes[1].set_title('MFCC коэффициенты')
            axes[1].set_ylabel('MFCC')
            
            # График сегментов
            for segment in segments:
                start_time = segment['start_time'] / 1000
                end_time = segment['end_time'] / 1000
                axes[2].axvspan(start_time, end_time, alpha=0.3)
                axes[2].text((start_time + end_time) / 2, 0.5, f"Сегмент {segment.get('segment_number', '?')}", 
                            ha='center', va='center')
            
            axes[2].set_title('Сегменты')
            axes[2].set_xlabel('Время (секунды)')
            axes[2].set_ylabel('Сегменты')
            
            plt.tight_layout()
            plt.savefig(viz_dir / 'intonation_segmentation.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Визуализация сохранена: {viz_dir / 'intonation_segmentation.png'}")
            
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить визуализацию: {e}")
    
    def _save_emotion_visualization(self, audio_path: str, features: np.ndarray, clusters: np.ndarray, segments: list):
        """Сохранение визуализации эмоциональной сегментации"""
        try:
            # Создаем папку для визуализаций
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            viz_dir = Path(f"data/audio_processing/{base_name}_visualizations")
            viz_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем график
            fig, axes = plt.subplots(2, 1, figsize=(15, 8))
            
            # График признаков
            if features.size > 0:
                times = np.arange(features.shape[1]) * 512 / 16000
                for i in range(min(5, features.shape[0])):  # Показываем первые 5 признаков
                    axes[0].plot(times, features[i], label=f'Признак {i+1}')
                axes[0].set_title('Эмоциональные признаки')
                axes[0].set_ylabel('Значение')
                axes[0].legend()
            
            # График кластеров
            if clusters.size > 0:
                times = np.arange(len(clusters)) * 512 / 16000
                scatter = axes[1].scatter(times, clusters, c=clusters, cmap='viridis')
                axes[1].set_title('Эмоциональные кластеры')
                axes[1].set_ylabel('Кластер')
                axes[1].set_xlabel('Время (секунды)')
                plt.colorbar(scatter, ax=axes[1])
            
            plt.tight_layout()
            plt.savefig(viz_dir / 'emotion_segmentation.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Визуализация сохранена: {viz_dir / 'emotion_segmentation.png'}")
            
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить визуализацию: {e}")
    
    def _save_energy_visualization(self, audio_path: str, energy: np.ndarray, zero_crossing_rate: np.ndarray, change_points: list, segments: list):
        """Сохранение визуализации энергетической сегментации"""
        try:
            # Создаем папку для визуализаций
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            viz_dir = Path(f"data/audio_processing/{base_name}_visualizations")
            viz_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем график
            fig, axes = plt.subplots(3, 1, figsize=(15, 10))
            
            # График энергии
            times = np.arange(len(energy)) * 512 / 16000
            axes[0].plot(times, energy)
            axes[0].set_title('Энергия сигнала')
            axes[0].set_ylabel('RMS')
            
            # Отмечаем точки изменения
            for change in change_points:
                change_time = change / 1000
                axes[0].axvline(x=change_time, color='red', alpha=0.7, linestyle='--')
            
            # График zero-crossing rate
            times_zcr = np.arange(len(zero_crossing_rate)) * 512 / 16000
            axes[1].plot(times_zcr, zero_crossing_rate)
            axes[1].set_title('Zero-Crossing Rate')
            axes[1].set_ylabel('ZCR')
            
            # График сегментов
            for segment in segments:
                start_time = segment['start_time'] / 1000
                end_time = segment['end_time'] / 1000
                axes[2].axvspan(start_time, end_time, alpha=0.3)
                axes[2].text((start_time + end_time) / 2, 0.5, f"Сегмент {segment.get('segment_number', '?')}", 
                            ha='center', va='center')
            
            axes[2].set_title('Сегменты')
            axes[2].set_xlabel('Время (секунды)')
            axes[2].set_ylabel('Сегменты')
            
            plt.tight_layout()
            plt.savefig(viz_dir / 'energy_segmentation.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Визуализация сохранена: {viz_dir / 'energy_segmentation.png'}")
            
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить визуализацию: {e}")
