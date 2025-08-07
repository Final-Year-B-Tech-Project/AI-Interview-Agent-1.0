# AI-Interview-Agent-1.0

graph TB
    subgraph "Client Layer (Browser)"
        UI[User Interface]
        WebSpeech[Web Speech API]
        TTS[Text-to-Speech]
        STT[Speech-to-Text Recognition]
        Camera[Camera/Webcam]
        Mic[Microphone]
        
        UI --> WebSpeech
        WebSpeech --> TTS
        WebSpeech --> STT
        Camera --> UI
        Mic --> STT
    end
    
    subgraph "Flask Backend Server"
        API[Flask API Routes]
        Auth[Authentication Service]
        InterviewCtrl[Interview Controller]
        VoiceService[Voice Processing Service]
        
        subgraph "Core Services"
            AIService[AI Service]
            InterviewSvc[Interview Service]
            UserMgmt[User Management]
        end
        
        API --> Auth
        API --> InterviewCtrl
        API --> VoiceService
        InterviewCtrl --> InterviewSvc
        InterviewCtrl --> AIService
    end
    
    subgraph "AI Processing Layer"
        OpenRouter[OpenRouter API]
        DeepSeek[DeepSeek R1T2 Chimera]
        Whisper[Whisper STT Model]
        Coqui[Coqui TTS Engine]
        
        OpenRouter --> DeepSeek
        AIService --> OpenRouter
        VoiceService --> Whisper
        VoiceService --> Coqui
    end
    
    subgraph "Data Layer"
        SQLite[(SQLite Database)]
        
        subgraph "Database Tables"
            Users[Users Table]
            Interviews[Interviews Table]
            Questions[Questions Table]
            Answers[Answers Table]
            Domains[Domains Table]
        end
        
        SQLite --> Users
        SQLite --> Interviews
        SQLite --> Questions
        SQLite --> Answers
        SQLite --> Domains
    end
    
    subgraph "External Services"
        GPU[GTX 1060 4GB GPU]
        FileSystem[Local File System]
        TempFiles[Temporary Audio Files]
        
        Coqui --> GPU
        VoiceService --> FileSystem
        FileSystem --> TempFiles
    end
    
    %% User Flow Connections
    User([User]) --> UI
    UI <--> API
    
    %% Data Flow
    API <--> SQLite
    InterviewSvc <--> SQLite
    UserMgmt <--> SQLite
    
    %% AI Processing Flow
    AIService --> |Question Generation| DeepSeek
    AIService --> |Answer Evaluation| DeepSeek
    AIService --> |Feedback Generation| DeepSeek
    
    %% Voice Processing Flow
    STT --> |Audio Data| VoiceService
    VoiceService --> |Transcribed Text| InterviewCtrl
    InterviewCtrl --> |Question Text| TTS
    
    %% Styling
    classDef clientLayer fill:#e1f5fe
    classDef serverLayer fill:#f3e5f5
    classDef aiLayer fill:#fff3e0
    classDef dataLayer fill:#e8f5e8
    classDef externalLayer fill:#fce4ec
    
    class UI,WebSpeech,TTS,STT,Camera,Mic clientLayer
    class API,Auth,InterviewCtrl,VoiceService,AIService,InterviewSvc,UserMgmt serverLayer
    class OpenRouter,DeepSeek,Whisper,Coqui aiLayer
    class SQLite,Users,Interviews,Questions,Answers,Domains dataLayer
    class GPU,FileSystem,TempFiles externalLayer
