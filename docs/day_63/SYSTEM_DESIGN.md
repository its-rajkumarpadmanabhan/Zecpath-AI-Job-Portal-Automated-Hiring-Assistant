# High-Scale System Design: Automated ATS & Voice Interviewing Engine

## 1. ATS Processing Architecture (Target: 100k Daily Resumes)
[ Client Upload ] ──> S3 Pre-Signed Upload URL (Bypass Application Server)
│
▼ (S3 Event Notification)
[ AWS SQS / RabbitMQ ]
│
▼
[ Celery Worker Pool (Autoscaling) ]
├── Step 1: Text Sanitization & PII Masking
├── Step 2: Embedding Generation (all-MiniLM-L6-v2)
├── Step 3: Cosine Similarity Scoring vs Job Requirements
└── Step 4: Batch Persistence to PostgreSQL (Index-Optimized)

## 2. Voice AI Interview Pipeline (Target: <300ms Audio Latency)
[ Candidate Browser (WebRTC) ] <──> [ Twilio Media Gateway / LiveKit ]
│ (Full-Duplex PCM Audio)
▼
[ Fast-Whisper Worker ]
│ (Transcribed Text)
▼
[ LLM Inference Engine ]
│ (Response Text & Score)
▼
[ ElevenLabs TTS Worker ]
│ (Audio Buffer)
▼
[ Twilio Media Stream Output ]
