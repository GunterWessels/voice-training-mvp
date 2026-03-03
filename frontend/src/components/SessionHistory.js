import React from 'react';

function SessionHistory({ sessions, onViewSession }) {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPersonaInfo = (personaId) => {
    const personas = {
      cfo: { name: 'Healthcare CFO', avatar: '💼' },
      clinical_director: { name: 'Clinical Director', avatar: '🩺' },
      it_director: { name: 'IT Director', avatar: '💻' },
      ceo: { name: 'Hospital CEO', avatar: '🏥' }
    };
    return personas[personaId] || { name: 'Unknown', avatar: '❓' };
  };

  const getStatusBadge = (status, score) => {
    if (status === 'completed') {
      if (score >= 80) return 'bg-green-100 text-green-800';
      if (score >= 60) return 'bg-yellow-100 text-yellow-800';
      return 'bg-red-100 text-red-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score > 0) return 'Needs Work';
    return 'In Progress';
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Training History
        </h2>
        <p className="text-gray-600">
          Review your past training sessions and track your progress
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🎙️</div>
          <h3 className="text-xl font-medium text-gray-900 mb-2">
            No training sessions yet
          </h3>
          <p className="text-gray-600 mb-4">
            Start your first training session to see your history here
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((session, idx) => {
            const persona = getPersonaInfo(session.persona_id);
            const prev = sessions[idx + 1];
            const hasScore = session.status === 'completed' && (session.score || 0) > 0;
            const prevHasScore = prev && prev.status === 'completed' && (prev.score || 0) > 0;
            const delta = (hasScore && prevHasScore) ? (session.score - prev.score) : null;

            return (
              <div
                key={session.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="text-3xl">{persona.avatar}</div>
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">
                        {persona.name}
                      </h3>
                      <p className="text-sm text-gray-600">
                        with {session.user_name} • {formatDate(session.created_at)}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    {/* Score + Trend */}
                    <div className="text-right space-y-1">
                      <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(session.status, session.score)}`}>
                        {session.score > 0 ? `${session.score}% - ${getScoreLabel(session.score)}` : getScoreLabel(session.score)}
                      </div>

                      {typeof delta === 'number' && (
                        <div className={`text-xs ${delta >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                          Trend vs prior: {delta >= 0 ? '+' : ''}{delta}
                        </div>
                      )}

                      {session.score_count > 0 && (
                        <div className="text-xs text-gray-500">AI checkpoints: {session.score_count}</div>
                      )}
                    </div>
                    
                    {/* View Button */}
                    <button
                      onClick={() => onViewSession(session.id)}
                      className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                    >
                      Review
                    </button>
                  </div>
                </div>

                {/* Session Stats */}
                <div className="mt-4 flex space-x-6 text-sm text-gray-600">
                  <div>
                    <span className="font-medium">Status:</span> {session.status}
                  </div>
                  {session.updated_at !== session.created_at && (
                    <div>
                      <span className="font-medium">Last Updated:</span> {formatDate(session.updated_at)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Summary Stats */}
      {sessions.length > 0 && (() => {
        const completed = sessions.filter(s => s.status === 'completed');
        const scored = completed.filter(s => (s.score || 0) > 0);
        const avg = scored.length > 0
          ? Math.round(scored.reduce((sum, s) => sum + (s.score || 0), 0) / scored.length)
          : 0;

        return (
          <div className="mt-8 bg-indigo-50 rounded-lg p-6">
            <h3 className="text-lg font-medium text-indigo-900 mb-4">
              📊 Your Training Progress
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">
                  {sessions.length}
                </div>
                <div className="text-sm text-indigo-800">Total Sessions</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">
                  {completed.length}
                </div>
                <div className="text-sm text-indigo-800">Completed</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">
                  {avg > 0 ? `${avg}%` : '—'}
                </div>
                <div className="text-sm text-indigo-800">Avg Score (Completed)</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">
                  {sessions.filter(s => (s.score || 0) >= 80).length}
                </div>
                <div className="text-sm text-indigo-800">Excellent Scores</div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

export default SessionHistory;