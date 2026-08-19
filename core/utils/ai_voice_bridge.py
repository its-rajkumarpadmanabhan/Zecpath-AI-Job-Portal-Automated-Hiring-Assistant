import os
import time
import logging
import requests
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class AIVoiceBridgeService:
    """
    Central service layer bridging Django with LLMs, Speech-to-Text (STT),
    Text-to-Speech (TTS), and Voice Call Telephony Gateways.
    """

    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY', ''))
        self.max_retries = getattr(settings, 'AI_SERVICE_MAX_RETRIES', 3)
        self.timeout = getattr(settings, 'AI_SERVICE_TIMEOUT_SECONDS', 15)
        
        # Initialize Gemini Client if API key is present
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    # ==========================================================================
    # 1. LLM Generation: Dynamic Interview Question Generation
    # ==========================================================================
    def generate_interview_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Sends prompts to the LLM with automated retry and fallback handling.
        """
        if not self.client:
            logger.warning("[AI Bridge] Gemini API key not set. Using simulated LLM fallback.")
            return "Simulated AI Response: Can you explain how you handle database connection pooling in Django?"

        for attempt in range(1, self.max_retries + 1):
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction or "You are an expert technical interviewer conducting a screening call.",
                    temperature=0.7,
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as exc:
                logger.error(f"[AI Bridge] LLM call failed (Attempt {attempt}/{self.max_retries}): {exc}")
                if attempt == self.max_retries:
                    # Graceful Fallback
                    return "Thank you for sharing. Could you tell me more about your recent project achievements?"
                time.sleep(1.5 * attempt)

    # ==========================================================================
    # 2. Text-to-Speech (TTS) Synthesis
    # ==========================================================================
    def synthesize_speech(self, text: str, voice_gender: str = 'female', language_code: str = 'en-US') -> dict:
        """
        Converts text prompts into synthesized voice audio payload or audio URL.
        """
        try:
            # Voice profile selection logic
            voice_id = "en-US-Neural2-F" if voice_gender == "female" else "en-US-Neural2-D"
            
            logger.info(f"[AI Bridge TTS] Synthesizing speech in '{language_code}' with voice '{voice_id}'...")
            
            # Simulated audio metadata payload (or integration with Google Cloud TTS / ElevenLabs)
            return {
                "status": "success",
                "text": text,
                "language_code": language_code,
                "voice_id": voice_id,
                "audio_format": "mp3",
                "audio_url": f"https://api.zecpath.com/media/audio/synth_{int(time.time())}.mp3",
                "duration_estimate_seconds": round(len(text.split()) * 0.4, 2)
            }
        except Exception as exc:
            logger.error(f"[AI Bridge TTS] Speech synthesis failed: {exc}")
            return {
                "status": "failed",
                "error": str(exc),
                "audio_url": None
            }

    # ==========================================================================
    # 3. Speech-to-Text (STT) Transcription
    # ==========================================================================
    def transcribe_audio(self, audio_source: str, language_code: str = 'en-US') -> dict:
        """
        Converts candidate spoken voice recordings into structured text transcripts.
        """
        try:
            logger.info(f"[AI Bridge STT] Transcribing voice input from: {audio_source}")
            
            # Simulated STT conversion engine (or Deepgram / Whisper / Google STT)
            return {
                "status": "success",
                "transcript": "I have extensive experience deploying Django applications with Redis and Celery inside Docker containers.",
                "confidence": 0.96,
                "language": language_code,
                "words_count": 14
            }
        except Exception as exc:
            logger.error(f"[AI Bridge STT] Audio transcription error: {exc}")
            return {
                "status": "failed",
                "transcript": "",
                "confidence": 0.0,
                "error": str(exc)
            }

    # ==========================================================================
    # 4. Outbound Voice Call Trigger (Telephony Gateway)
    # ==========================================================================
    def trigger_outbound_call(self, to_phone_number: str, candidate_name: str, job_title: str) -> dict:
        """
        Initiates an outbound automated voice screening call via Telephony Gateway.
        """
        if not to_phone_number:
            raise ValueError("Recipient phone number is required.")

        try:
            logger.info(f"[AI Bridge Telephony] Triggering outbound call to {to_phone_number} ({candidate_name}) for '{job_title}'...")
            
            # Simulate Telephony Handshake & Webhook Setup
            call_sid = f"CA_{int(time.time())}_{to_phone_number[-4:]}"
            
            return {
                "status": "queued",
                "call_sid": call_sid,
                "to": to_phone_number,
                "candidate": candidate_name,
                "job_title": job_title,
                "gateway": settings.VOICE_SERVICE_PROVIDER,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        except Exception as exc:
            logger.error(f"[AI Bridge Telephony] Call trigger failed: {exc}")
            return {
                "status": "failed",
                "error": str(exc)
            }
