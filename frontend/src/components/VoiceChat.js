import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function VoiceChat({ session, onEndSession }) {
  const [messages, setMessages] = useState(session.messages || []);
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);
  const [ttsProvider, setTtsProvider] = useState('browser');
  
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    connectWebSocket();
    setupSpeechRecognition();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const connectWebSocket = () => {
    const wsUrl = `ws://localhost:8000/ws/${session.session_id}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'ai_message') {
        const aiMessage = {
          speaker: 'ai',
          text: data.text,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, aiMessage]);
        
        // Update TTS provider info
        if (data.tts_provider) {
          setTtsProvider(data.tts_provider);
        }
        
        // Handle audio playback
        if (data.audio && data.audio.audio_data) {
          // High-quality TTS audio from backend (ElevenLabs/OpenAI)
          playHighQualityAudio(data.audio.audio_data, data.audio.content_type, data.text);
        } else {
          // Fallback to improved browser TTS
          speakTextImproved(data.text);
        }
      } else if (data.type === 'ready') {
        console.log('WebSocket ready');
        if (data.tts_info) {
          setTtsProvider(data.tts_info.current_provider);
        }
      } else if (data.error) {
        console.error('WebSocket error:', data.error);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  };

  const setupSpeechRecognition = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          }
        }

        if (finalTranscript) {
          sendMessage(finalTranscript.trim());
        }
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }
  };

  const startRecording = () => {
    if (recognitionRef.current && isConnected) {
      setIsRecording(true);
      recognitionRef.current.start();
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendMessage = (text) => {
    if (!text.trim() || !isConnected) return;

    const userMessage = {
      speaker: 'user',
      text: text,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    
    wsRef.current.send(JSON.stringify({
      type: 'user_message',
      text: text
    }));
    
    setTextInput('');
  };

  const handleTextSubmit = (e) => {
    e.preventDefault();
    sendMessage(textInput);
  };

  const playHighQualityAudio = (audioData, contentType, fallbackText = '') => {
    try {
      // Convert base64 to audio blob
      const binaryString = window.atob(audioData);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const audioBlob = new Blob([bytes], { type: contentType });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      // Create and play audio
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play().catch(e => {
          console.error('Audio play error:', e);
          // Fallback to browser TTS if audio fails to play
          if (fallbackText) {
            speakTextImproved(fallbackText);
          }
        });
        
        // Clean up URL after playing
        audioRef.current.onended = () => {
          URL.revokeObjectURL(audioUrl);
        };
      }
    } catch (error) {
      console.error('Error playing high-quality audio:', error);
      // Fallback to browser TTS
      if (fallbackText) {
        speakTextImproved(fallbackText);
      }
    }
  };

  const speakTextImproved = (text) => {
    if ('speechSynthesis' in window) {
      // Cancel any ongoing speech
      speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.85; // Slightly slower for better clarity
      utterance.pitch = 1.0;
      utterance.volume = 0.9;
      
      // Find the best available English voice
      const voices = speechSynthesis.getVoices();
      
      // Prefer higher quality voices (usually premium/enhanced voices)
      const preferredVoices = voices.filter(voice => 
        voice.lang.startsWith('en') && 
        (voice.name.includes('Premium') || 
         voice.name.includes('Enhanced') ||
         voice.name.includes('Neural') ||
         voice.name.includes('Google') ||
         voice.name.includes('Microsoft'))
      );
      
      // Fallback to any English voice
      const englishVoices = voices.filter(voice => voice.lang.startsWith('en'));
      
      const selectedVoice = preferredVoices[0] || englishVoices[0] || voices[0];
      
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }
      
      speechSynthesis.speak(utterance);
    }
  };

  const endSession = async () => {
    try {
      await axios.post(`/sessions/${session.session_id}/score`);
    } catch (error) {
      console.error('Error scoring session:', error);
    }
    onEndSession();
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-indigo-600 text-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-2xl mr-3">{session.persona.avatar}</span>
            <div>
              <h2 className="text-xl font-semibold">{session.persona.name}</h2>
              <div className="text-indigo-200 text-sm">
                <div>{isConnected ? '🟢 Connected' : '🔴 Disconnected'}</div>
                <div className="text-xs">
                  Voice: {ttsProvider === 'elevenlabs' ? '🎤 Premium' : 
                          ttsProvider === 'openai' ? '🔊 High Quality' : 
                          '📢 Standard'}
                </div>
              </div>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowTextInput(!showTextInput)}
              className="px-3 py-1 text-sm bg-indigo-500 hover:bg-indigo-400 rounded"
            >
              {showTextInput ? 'Hide Text' : 'Show Text'}
            </button>
            <button
              onClick={endSession}
              className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded"
            >
              End Session
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="h-96 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.speaker === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-900'
              }`}
            >
              <p className="text-sm">{message.text}</p>
              <p className={`text-xs mt-1 ${
                message.speaker === 'user' ? 'text-indigo-200' : 'text-gray-500'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Controls */}
      <div className="border-t bg-gray-50 p-4">
        {/* Voice Controls */}
        <div className="flex justify-center mb-4">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={!isConnected}
            className={`px-8 py-4 rounded-full text-white font-semibold transition-all duration-200 ${
              isRecording
                ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                : 'bg-indigo-600 hover:bg-indigo-700'
            } ${!isConnected ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isRecording ? '🔴 Stop Recording' : '🎙️ Start Recording'}
          </button>
        </div>

        {/* Text Input (Optional) */}
        {showTextInput && (
          <form onSubmit={handleTextSubmit} className="flex space-x-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={!textInput.trim() || !isConnected}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-300"
            >
              Send
            </button>
          </form>
        )}

        {/* Instructions */}
        <div className="text-center mt-3">
          <p className="text-sm text-gray-600">
            🎯 Practice your pitch • {ttsProvider === 'elevenlabs' ? '🎤 Premium voice quality' : 
                                      ttsProvider === 'openai' ? '🔊 High-quality AI voice' : 
                                      '📢 Browser voice'} • ⏰ Session auto-saves
          </p>
        </div>
      </div>
      
      {/* Hidden audio element for high-quality TTS playback */}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

export default VoiceChat;