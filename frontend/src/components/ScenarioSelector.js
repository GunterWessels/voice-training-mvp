import React, { useEffect, useState } from 'react';
import axios from 'axios';

function ScenarioSelector({ cartridgeId, persona, userName, onBack, onStart }) {
  const [loading, setLoading] = useState(true);
  const [cartridge, setCartridge] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      if (!cartridgeId) return;
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`/cartridges/${cartridgeId}`);
        const data = response.data;
        setCartridge(data.cartridge);

        const scenarioList =
          (data.rag_context && data.rag_context.available_scenarios) ||
          (data.cartridge && data.cartridge.scenarios) ||
          [];
        setScenarios(scenarioList);
      } catch (e) {
        console.error('Error loading cartridge scenarios:', e);
        setError('Failed to load scenarios.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [cartridgeId]);

  if (!cartridgeId) {
    return (
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-6">
        <p className="text-gray-700">No cartridge selected.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Select a Scenario</h2>
            <p className="text-gray-600 mt-1">
              Cartridge: <span className="font-medium">{cartridge?.name || 'Practice Cartridge'}</span>
            </p>
            <p className="text-gray-600">
              Persona: <span className="font-medium">{persona?.name || persona?.id}</span> | You: <span className="font-medium">{userName}</span>
            </p>
          </div>
          <button
            onClick={onBack}
            className="px-3 py-2 rounded-md text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            Back
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {scenarios.length === 0 ? (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-yellow-800">No scenarios found in this cartridge.</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {scenarios.map((s) => (
              <div key={s.id} className="border rounded-lg p-4 hover:shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{s.name}</h3>
                    <p className="text-sm text-gray-600">{s.description}</p>
                    <div className="mt-2 text-xs text-gray-500 space-x-3">
                      <span>Type: {s.type}</span>
                      <span>Difficulty: {s.difficulty}</span>
                      <span>Duration: {s.duration_minutes}m</span>
                    </div>
                  </div>
                  <button
                    onClick={() => onStart(s)}
                    className="shrink-0 px-3 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
                  >
                    Start
                  </button>
                </div>

                {Array.isArray(s.success_criteria) && s.success_criteria.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-700 mb-1">Success criteria</p>
                    <ul className="list-disc ml-5 text-xs text-gray-600 space-y-1">
                      {s.success_criteria.slice(0, 4).map((c, idx) => (
                        <li key={idx}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ScenarioSelector;
