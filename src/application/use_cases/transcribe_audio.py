"""Use case: Full audio transcription with diarization."""
from __future__ import annotations

import asyncio
import logging
import tempfile
import time

from src.application.dto.schemas import (
    SegmentResult,
    TimingResult,
    TranscribeResult,
)
from src.domain.chilean_spanish import post_process_chilean_spanish
from src.domain.entities.transcript import Segment, Speaker, Transcript
from src.domain.entities.transcript import DiarizationTurn
from src.domain.ports.interfaces import (
    ASRPort,
    AudioFilePort,
    AudioProcessorPort,
    DiarizationPort,
    TranscriptIndexPort,
    TranscriptStorePort,
)

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    "es-CL": "es",
    "es": "es",
    "en-US": "en",
    "en": "en",
    "pt": "pt",
    "pt-BR": "pt",
}


class TranscribeAudioUseCase:
    """Orchestrates: save → preprocess → diarize → transcribe → persist."""

    def __init__(
        self,
        asr: ASRPort,
        diarizer: DiarizationPort,
        processor: AudioProcessorPort,
        store: TranscriptStorePort,
        audio_files: AudioFilePort,
        index: TranscriptIndexPort | None = None,
    ):
        self._asr = asr
        self._diarizer = diarizer
        self._processor = processor
        self._store = store
        self._audio_files = audio_files
        self._index = index

    async def execute(
        self,
        filename: str,
        content: bytes,
        dest_dir: str,
        params: dict,
    ) -> TranscribeResult:
        t_global = time.time()
        language = params.get("language", "es-CL")
        model_size = params.get("model_size", "large-v3")
        min_speakers = params.get("min_speakers", 1)
        max_speakers = params.get("max_speakers", 2)
        vad_threshold = params.get("vad_threshold", 0.25)
        keep_cache = params.get("keep_cache", True)
        progress_callback = params.get("progress_callback")
        current_progress = 0

        async def emit_progress(stage: str, progress: int, message: str, extra: dict | None = None):
            nonlocal current_progress
            current_progress = max(current_progress, int(progress))
            if callable(progress_callback):
                try:
                    progress_callback(stage, int(progress), message, extra)
                except Exception:
                    logger.debug("[progress] callback failed", exc_info=True)
            await asyncio.sleep(0)

        audio_path = None
        processed_path = None

        # Parse suppress_tokens
        suppress_tokens_raw = params.get("suppress_tokens", "-1")
        if suppress_tokens_raw.strip() == "-1":
            parsed_suppress_tokens = [-1]
        else:
            try:
                parsed_suppress_tokens = [int(x) for x in suppress_tokens_raw.split(",") if x.strip()]
            except ValueError:
                parsed_suppress_tokens = [-1]

        try:
            await emit_progress("upload", 4, "Upload recebido")

            # 1. Save upload
            t_step = time.time()
            audio_path = await self._audio_files.save_upload(filename, content, dest_dir)
            save_elapsed = time.time() - t_step
            logger.info(f"[save] stored {audio_path} size={len(content)}B elapsed={save_elapsed:.2f}s")
            await emit_progress("upload", 10, "Arquivo salvo", {"bytes": len(content)})

            # 2. Convert to WAV
            t_step = time.time()
            audio_path = self._audio_files.convert_to_wav(audio_path)
            convert_elapsed = time.time() - t_step
            await emit_progress("preprocess", 18, "Convertendo para WAV")

            # 3. Preprocess
            t_step = time.time()
            processed_path = self._processor.process(audio_path, {
                "noise_reduce": params.get("noise_reduce", True),
                "reduction_db": params.get("reduction_db", 25),
                "voice_enhance": params.get("voice_enhance", True),
                "apply_gain": params.get("apply_gain", True),
                "target_lufs": params.get("target_lufs", -16.0),
                "remove_silence": params.get("remove_silence", True),
                "silence_thresh": params.get("silence_thresh", -45),
                "min_silence_len": params.get("min_silence_len", 250),
            })
            preprocess_elapsed = time.time() - t_step
            logger.info(f"[prep] processed={processed_path} elapsed={preprocess_elapsed:.2f}s")
            await emit_progress("preprocess", 42, "Pré-processamento concluído")

            # 4. Diarization
            t_step = time.time()
            diarization_fallback = False
            diarization_fallback_reason = None
            await emit_progress("diarization", 50, "Iniciando diarização")
            try:
                turns = self._diarizer.diarize(
                    processed_path,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    vad_threshold=vad_threshold,
                )
            except ValueError as e:
                if "Pyannote auth token missing" not in str(e):
                    raise
                duration_s = float(self._audio_files.get_duration(processed_path))
                turns = [
                    DiarizationTurn(
                        speaker="SPEAKER_00",
                        start=0.0,
                        end=duration_s,
                    )
                ]
                diarization_fallback = True
                diarization_fallback_reason = "pyannote_token_missing"
                logger.warning(
                    "[diarization] pyannote token missing; fallback to single-speaker mode duration=%.2fs",
                    duration_s,
                )
            except Exception as e:
                duration_s = float(self._audio_files.get_duration(processed_path))
                turns = [
                    DiarizationTurn(
                        speaker="SPEAKER_00",
                        start=0.0,
                        end=duration_s,
                    )
                ]
                diarization_fallback = True
                diarization_fallback_reason = "pyannote_runtime_unavailable"
                logger.warning(
                    "[diarization] unavailable (%s); fallback to single-speaker mode duration=%.2fs",
                    e,
                    duration_s,
                )

            if not turns:
                duration_s = float(self._audio_files.get_duration(processed_path))
                turns = [
                    DiarizationTurn(
                        speaker="SPEAKER_00",
                        start=0.0,
                        end=duration_s,
                    )
                ]
                diarization_fallback = True
                diarization_fallback_reason = "pyannote_empty_turns"
                logger.warning(
                    "[diarization] no speaker turns returned; fallback to single-speaker mode duration=%.2fs",
                    duration_s,
                )

            diarization_elapsed = time.time() - t_step
            logger.info(f"[diarization] segments={len(turns)} elapsed={diarization_elapsed:.2f}s")
            await emit_progress(
                "diarization",
                65,
                f"Diarização concluída com {len(turns)} segmentos",
                {
                    "segments": len(turns),
                    "fallback": diarization_fallback,
                    "fallback_reason": diarization_fallback_reason,
                },
            )

            # 5. Transcribe each segment
            t_step = time.time()
            model_load_elapsed = 0.0  # tracked inside adapter
            segments: list[SegmentResult] = []
            transcription_elapsed_total = 0.0

            whisper_lang = LANGUAGE_MAP.get(language, "es")
            total_turns = max(1, len(turns))

            for idx, turn in enumerate(turns, 1):
                progress_before_segment = 66 + int(((idx - 1) / total_turns) * 27)
                await emit_progress(
                    "transcription",
                    progress_before_segment,
                    f"Transcrevendo segmento {idx}/{total_turns}",
                    {"segment_index": idx, "segment_total": total_turns},
                )

                seg_start_ms = int(turn.start * 1000)
                seg_end_ms = int(turn.end * 1000)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as seg_file:
                    seg_path = self._audio_files.extract_segment(
                        processed_path, seg_start_ms, seg_end_ms, seg_file.name
                    )

                t_seg = time.time()
                raw_text = self._asr.transcribe(
                    seg_path,
                    language=whisper_lang,
                    model_size=model_size,
                    temperature=params.get("whisper_temp", 0.0),
                    beam_size=params.get("beam_size", 5),
                    best_of=params.get("best_of", 5),
                    compression_ratio_threshold=params.get("compression_ratio_threshold", 2.4),
                    logprob_threshold=params.get("logprob_threshold", -1.0),
                    no_speech_threshold=params.get("no_speech_threshold", 0.6),
                    condition_on_previous_text=params.get("condition_on_previous_text", False),
                    initial_prompt=params.get("initial_prompt"),
                    length_penalty=params.get("length_penalty", 1.0),
                    patience=params.get("patience"),
                    suppress_blank=params.get("suppress_blank", True),
                    suppress_tokens=parsed_suppress_tokens,
                    word_timestamps=params.get("word_timestamps", False),
                )
                seg_elapsed = time.time() - t_seg
                transcription_elapsed_total += seg_elapsed

                # Clean up temp segment file
                import os
                if os.path.exists(seg_path):
                    os.remove(seg_path)

                text = post_process_chilean_spanish(raw_text)
                logger.info(
                    f"[segment {idx}] speaker={turn.speaker} "
                    f"{turn.start:.2f}-{turn.end:.2f}s chars={len(text)} elapsed={seg_elapsed:.2f}s"
                )

                progress_after_segment = 66 + int((idx / total_turns) * 27)
                await emit_progress(
                    "transcription",
                    progress_after_segment,
                    f"Segmento {idx}/{total_turns} concluído",
                    {
                        "segment_index": idx,
                        "segment_total": total_turns,
                        "speaker": turn.speaker,
                    },
                )

                segments.append(SegmentResult(
                    index=idx,
                    speaker=turn.speaker,
                    start=turn.start,
                    end=turn.end,
                    duration=turn.duration,
                    text=text,
                ))

            # 6. Persist transcript
            transcript_id = f"transcript_{int(time.time())}"
            domain_segments = [
                Segment(
                    index=s.index,
                    speaker=Speaker(label=s.speaker),
                    start=s.start,
                    end=s.end,
                    text=s.text,
                )
                for s in segments
            ]
            transcript = Transcript(
                transcript_id=transcript_id,
                segments=domain_segments,
                source_file=filename,
                language=language,
            )
            self._store.save(transcript)
            await emit_progress("transcription", 95, "Transcrição consolidada")

            # 7. Auto-index into vector store (if configured)
            if self._index is not None:
                try:
                    n = await self._index.index(transcript)
                    logger.info("[qdrant] auto-indexed %d segments for %s", n, transcript_id)
                except Exception as e:
                    logger.warning("[qdrant] auto-index failed: %s", e)

            total_elapsed = time.time() - t_global
            logger.info(
                "[summary] file='%s' total=%.2fs save=%.2f convert=%.2f "
                "preprocess=%.2f diar=%.2f transcribe=%.2f segments=%d",
                filename, total_elapsed, save_elapsed, convert_elapsed,
                preprocess_elapsed, diarization_elapsed,
                transcription_elapsed_total, len(segments),
            )
            await emit_progress("transcription", 100, "Concluído", {"transcript_id": transcript_id})

            return TranscribeResult(
                transcript_id=transcript_id,
                segments=segments,
                timings=TimingResult(
                    save_s=round(save_elapsed, 2),
                    convert_s=round(convert_elapsed, 2),
                    preprocess_s=round(preprocess_elapsed, 2),
                    diarization_s=round(diarization_elapsed, 2),
                    model_load_s=round(model_load_elapsed, 2),
                    transcription_s=round(transcription_elapsed_total, 2),
                    total_s=round(total_elapsed, 2),
                ),
                params={
                    "model_size": model_size,
                    "language": language,
                    "diarization_fallback": diarization_fallback,
                    "diarization_fallback_reason": diarization_fallback_reason,
                    "beam_size": params.get("beam_size", 5),
                    "best_of": params.get("best_of", 5),
                    "temperature": params.get("whisper_temp", 0.0),
                    "vad_threshold": vad_threshold,
                    "noise_reduce": params.get("noise_reduce", True),
                    "reduction_db": params.get("reduction_db", 25),
                    "voice_enhance": params.get("voice_enhance", True),
                    "apply_gain": params.get("apply_gain", True),
                    "target_lufs": params.get("target_lufs", -16.0),
                    "remove_silence": params.get("remove_silence", True),
                    "silence_thresh": params.get("silence_thresh", -45),
                    "min_silence_len": params.get("min_silence_len", 250),
                    "word_timestamps": params.get("word_timestamps", False),
                },
            )

        except Exception as e:
            await emit_progress("transcription", max(current_progress, 1), f"Erro: {e}", {"error": str(e)})
            raise

        finally:
            import contextlib
            import os
            if processed_path and os.path.exists(processed_path):
                with contextlib.suppress(Exception):
                    os.remove(processed_path)
            if audio_path and os.path.exists(audio_path):
                with contextlib.suppress(Exception):
                    os.remove(audio_path)
            if not keep_cache and hasattr(self._asr, "clear_cache"):
                self._asr.clear_cache()
