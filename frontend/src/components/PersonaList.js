import React, { useState } from 'react';

function PersonaList({ personas, hasCartridge = false, onSelectPersona }) {
  const [userName, setUserName] = useState('Sales Rep');

  const handleSelectPersona = (personaId) => {
    onSelectPersona(personaId, userName);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Choose Your Training Partner
        </h2>
        <p className="text-lg text-gray-600 mb-6">
          Select an AI persona to practice your MedTech sales pitch with
        </p>
        
        {/* User Name Input */}
        <div className="max-w-md mx-auto mb-8">
          <label htmlFor="userName" className="block text-sm font-medium text-gray-700 mb-2">
            Your Name
          </label>
          <input
            type="text"
            id="userName"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Enter your name"
          />
        </div>
      </div>

      {/* Persona Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {personas.map((persona) => (
          <div
            key={persona.id}
            className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 p-6"
          >
            <div className="text-center mb-4">
              <div className="text-4xl mb-2">{persona.avatar}</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {persona.name}
              </h3>
              <p className="text-gray-600 text-sm">
                {persona.description}
              </p>
            </div>
            
            <button
              onClick={() => handleSelectPersona(persona.id)}
              disabled={!userName.trim()}
              className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200"
            >
              {hasCartridge ? 'Next: Select Scenario' : 'Start Training'}
            </button>
          </div>
        ))}
      </div>

      {/* Instructions */}
      <div className="mt-12 bg-blue-50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-blue-900 mb-2">
          💡 Training Tips
        </h3>
        <ul className="text-blue-800 space-y-1 text-sm">
          <li>• Click "Start Recording" to use voice-to-text</li>
          <li>• Practice your value proposition and handle objections</li>
          <li>• Each persona has different priorities and concerns</li>
          <li>• Sessions are automatically saved for review</li>
          <li>• Get a score and feedback when you finish</li>
        </ul>
      </div>
    </div>
  );
}

export default PersonaList;