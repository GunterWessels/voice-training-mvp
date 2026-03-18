import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import RoastCard from './RoastCard';

function EnhancedVoiceChat({ session, onEndSession }) {
  const [messages, setMessages] = useState(session.messages || []);
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);
  const [showFeaturePanel, setShowFeaturePanel] = useState(false);
  const [features, setFeatures] = useState({
    instructions: true,
    coaching: true,
    feedback: true,
    assessment: false,
    evaluation: false,
    practice_loops: true,
    objection_handling: true,
    time_pressure: false,
    difficulty_scaling: true
  });
  const [coaching, setCoaching] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [roastData, setRoastData] = useState(null);
  const [roastError, setRoastError] = useState(false);
  const [roastLoading, setRoastLoading] = useState(false);
  
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    connectWebSocket();
    setupSpeechRecognition();
    
    // Load cartridge features if available
    if (session.cartridge) {
      loadCartridgeFeatures();
    }
    
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

  const loadCartridgeFeatures = async () => {
    if (!session.cartridge?.id) return;
    
    try {
      const response = await axios.get(`/cartridges/${session.cartridge.id}`);
      const cartridgeFeatures = response.data.active_features;
      setFeatures(cartridgeFeatures);
    } catch (error) {
      console.error('Error loading cartridge features:', error);
    }
  };

  const updateFeatures = async (newFeatures) => {
    if (!session.cartridge?.id) {
      setFeatures(newFeatures);
      return;
    }

    try {
      await axios.put(`/cartridges/${session.cartridge.id}/features`, newFeatures);
      setFeatures(newFeatures);
      console.log('Features updated successfully');
    } catch (error) {
      console.error('Error updating features:', error);
    }
  };

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
        
        // Handle coaching hints
        if (data.coaching) {
          setCoaching(data.coaching);
        }
        
        // Handle feedback
        if (data.feedback) {
          setFeedback(data.feedback);
        }
        
        // Handle audio playback (high-quality audio from backend when available)
        if (data.audio && data.audio.audio_data) {
          playHighQualityAudio(data.audio.audio_data, data.audio.content_type, data.text);
        } else {
          // Fallback to browser TTS
          speakText(data.text);
        }
        
      } else if (data.type === 'ready') {
        console.log('WebSocket ready');
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

  const playHighQualityAudio = async (base64Audio, contentType = 'audio/mpeg', fallbackText = '') => {
    try {
      setIsPlayingAudio(true);

      // Convert base64 to blob and play
      const audioBytes = atob(base64Audio);
      const audioArray = new Uint8Array(audioBytes.length);
      for (let i = 0; i < audioBytes.length; i++) {
        audioArray[i] = audioBytes.charCodeAt(i);
      }

      const audioBlob = new Blob([audioArray], { type: contentType || 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);

      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setIsPlayingAudio(false);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = (error) => {
        console.error('Audio playback error:', error);
        setIsPlayingAudio(false);
        URL.revokeObjectURL(audioUrl);

        // Fallback to browser TTS
        if (fallbackText) {
          speakText(fallbackText);
        }
      };

      await audio.play();
      console.log('🎵 Playing AI audio');

    } catch (error) {
      console.error('Error playing AI audio:', error);
      setIsPlayingAudio(false);

      // Fallback to browser TTS
      if (fallbackText) {
        speakText(fallbackText);
      }
    }
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
      
      // Clear previous coaching/feedback
      setCoaching(null);
      setFeedback(null);
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

  const speakText = (text) => {
    // Fallback TTS if ElevenLabs audio isn't available
    if ('speechSynthesis' in window && !isPlayingAudio) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1.0;
      
      const voices = speechSynthesis.getVoices();
      const voice = voices.find(v => v.lang.startsWith('en')) || voices[0];
      if (voice) {
        utterance.voice = voice;
      }
      
      speechSynthesis.speak(utterance);
    }
  };

  const endSession = async () => {
    // Score the session (best effort — don't block on failure)
    try {
      await axios.post(`/sessions/${session.session_id}/score`);
    } catch (error) {
      console.error('Error scoring session:', error);
    }

    // Trigger roast generation
    setRoastLoading(true);
    try {
      const response = await axios.post(
        `/sessions/${session.session_id}/roast`,
        {},
        { timeout: 20000 }  // 20s client-side timeout (backend is 15s)
      );
      setRoastData(response.data);
    } catch (error) {
      console.error('Roast generation failed:', error);
      setRoastError(true);
    } finally {
      setRoastLoading(false);
    }
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

  const toggleFeature = (featureName) => {
    const newFeatures = {
      ...features,
      [featureName]: !features[featureName]
    };
    updateFeatures(newFeatures);
  };

  return (
    <div className="max-w-6xl mx-auto bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-indigo-600 text-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-2xl mr-3">{session.persona.avatar}</span>
            <div>
              <h2 className="text-xl font-semibold">{session.persona.name}</h2>
              <p className="text-indigo-200 text-sm">
                {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                {session.cartridge && ` • ${session.cartridge.name}`}
              </p>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowFeaturePanel(!showFeaturePanel)}
              className="px-3 py-1 text-sm bg-indigo-500 hover:bg-indigo-400 rounded"
            >
              Features
            </button>
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

      <div className="flex">
        {/* Main Chat Area */}
        <div className="flex-1">
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
            
            {/* Audio Playing Indicator */}
            {isPlayingAudio && (
              <div className="flex justify-start">
                <div className="bg-green-100 border border-green-200 rounded-lg px-4 py-2">
                  <p className="text-sm text-green-700">🔊 Playing AI audio...</p>
                </div>
              </div>
            )}
            
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
                🎯 Practice with {session.persona.name} • 🔊 Enhanced ElevenLabs voice • ⏰ Session auto-saves
              </p>
            </div>
          </div>
        </div>

        {/* Feature Panel */}
        {showFeaturePanel && (
          <div className="w-80 border-l bg-gray-50 p-4">
            <h3 className="font-semibold text-lg mb-4">Training Features</h3>
            
            <div className="space-y-3">
              {Object.entries(features).map(([featureName, isEnabled]) => (
                <div key={featureName} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 capitalize">
                    {featureName.replace('_', ' ')}
                  </span>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => toggleFeature(featureName)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
              ))}
            </div>

            {/* Coaching Panel */}
            {features.coaching && coaching && (
              <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-2">💡 Coaching Hints</h4>
                {coaching.suggestions && coaching.suggestions.length > 0 && (
                  <div className="mb-2">
                    <p className="text-xs font-medium text-blue-700">Suggestions:</p>
                    <ul className="text-xs text-blue-600">
                      {coaching.suggestions.map((suggestion, index) => (
                        <li key={index}>• {suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {coaching.improvements && coaching.improvements.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-blue-700">Improvements:</p>
                    <ul className="text-xs text-blue-600">
                      {coaching.improvements.map((improvement, index) => (
                        <li key={index}>• {improvement}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Feedback Panel */}
            {features.feedback && feedback && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h4 className="font-medium text-yellow-800 mb-2">📊 Performance Feedback</h4>
                <div className="text-sm text-yellow-700">
                  <p>Score: <span className="font-medium">{feedback.score}/100</span></p>
                  {feedback.strengths && feedback.strengths.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-medium">Strengths:</p>
                      <ul className="text-xs">
                        {feedback.strengths.map((strength, index) => (
                          <li key={index}>✅ {strength}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {feedback.areas_for_improvement && feedback.areas_for_improvement.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-medium">Areas for Improvement:</p>
                      <ul className="text-xs">
                        {feedback.areas_for_improvement.map((area, index) => (
                          <li key={index}>🔧 {area}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {(roastLoading || roastData || roastError) && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.75)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          zIndex: 9999,
        }}>
          <RoastCard
            roastData={roastLoading ? null : roastData}
            error={roastError}
          />
          {!roastLoading && (
            <button
              onClick={onEndSession}
              style={{
                marginTop: 16,
                background: 'transparent',
                color: '#aaa',
                border: '1px solid #555',
                borderRadius: 8,
                padding: '8px 20px',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              Close
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default EnhancedVoiceChat;