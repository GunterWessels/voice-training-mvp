import React, { useState, useEffect } from 'react';
import axios from 'axios';
import PersonaList from './components/PersonaList';
import VoiceChat from './components/VoiceChat';
import EnhancedVoiceChat from './components/EnhancedVoiceChat';
import CartridgeSelector from './components/CartridgeSelector';
import SessionHistory from './components/SessionHistory';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('cartridges'); // cartridges, personas, chat, history
  const [personas, setPersonas] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [selectedCartridge, setSelectedCartridge] = useState(null);

  useEffect(() => {
    loadPersonas();
    loadSessionHistory();
  }, []);

  const loadPersonas = async () => {
    try {
      const response = await axios.get('/personas');
      setPersonas(response.data.personas);
    } catch (error) {
      console.error('Error loading personas:', error);
    }
  };

  const loadSessionHistory = async () => {
    try {
      const response = await axios.get('/sessions');
      setSessionHistory(response.data.sessions);
    } catch (error) {
      console.error('Error loading session history:', error);
    }
  };

  const handleCartridgeSelect = (cartridgeId) => {
    setSelectedCartridge(cartridgeId);
    setCurrentView('personas');
  };

  const handleCartridgeCreate = (cartridgeId) => {
    setSelectedCartridge(cartridgeId);
    setCurrentView('personas');
  };

  const startSession = async (personaId, userName = 'User') => {
    try {
      const sessionData = {
        persona_id: personaId,
        user_name: userName
      };
      
      // Include cartridge if selected
      if (selectedCartridge) {
        sessionData.cartridge_id = selectedCartridge;
      }
      
      const response = await axios.post('/sessions', sessionData);
      
      setCurrentSession(response.data);
      setCurrentView('chat');
    } catch (error) {
      console.error('Error starting session:', error);
      alert('Failed to start session. Please try again.');
    }
  };

  const endSession = () => {
    setCurrentSession(null);
    setSelectedCartridge(null);
    setCurrentView('cartridges');
    loadSessionHistory(); // Refresh history
  };

  const viewSession = async (sessionId) => {
    try {
      const response = await axios.get(`/sessions/${sessionId}`);
      setCurrentSession({
        session_id: sessionId,
        persona: response.data.persona,
        session: response.data.session,
        messages: response.data.messages
      });
      setCurrentView('chat');
    } catch (error) {
      console.error('Error loading session:', error);
    }
  };

  const goToCartridges = () => {
    setSelectedCartridge(null);
    setCurrentView('cartridges');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">
                🎙️ Enhanced Voice Training Platform
              </h1>
              <span className="ml-3 text-sm text-indigo-600 font-medium">
                with ElevenLabs & Practice Cartridges
              </span>
            </div>
            <nav className="flex space-x-4">
              <button
                onClick={goToCartridges}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  currentView === 'cartridges'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Practice Cartridges
              </button>
              <button
                onClick={() => setCurrentView('personas')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  currentView === 'personas'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                disabled={!selectedCartridge}
              >
                Select Persona {selectedCartridge && '✓'}
              </button>
              <button
                onClick={() => setCurrentView('history')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  currentView === 'history'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                History
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {currentView === 'cartridges' && (
          <CartridgeSelector
            onSelectCartridge={handleCartridgeSelect}
            onCreateCartridge={handleCartridgeCreate}
          />
        )}

        {currentView === 'personas' && (
          <div>
            {selectedCartridge && (
              <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-green-800">
                  ✓ Cartridge selected. Choose a persona to start your practice session.
                </p>
              </div>
            )}
            <PersonaList
              personas={personas}
              onStartSession={startSession}
            />
          </div>
        )}

        {currentView === 'chat' && currentSession && (
          // Use enhanced chat if cartridge is present, regular chat otherwise
          currentSession.cartridge ? (
            <EnhancedVoiceChat
              session={currentSession}
              onEndSession={endSession}
            />
          ) : (
            <VoiceChat
              session={currentSession}
              onEndSession={endSession}
            />
          )
        )}

        {currentView === 'history' && (
          <SessionHistory
            sessions={sessionHistory}
            onViewSession={viewSession}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            LiquidSMARTS™ Enhanced Voice Training Platform • ElevenLabs TTS • Practice Cartridges • Toggleable Training Features
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;