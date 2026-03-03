import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

function CartridgeSelector({ onSelectCartridge, onCreateCartridge }) {
  const [cartridges, setCartridges] = useState([]);
  const [promptCartridges, setPromptCartridges] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCreatePromptForm, setShowCreatePromptForm] = useState(false);
  const [showAttachPromptForm, setShowAttachPromptForm] = useState(false);
  const [attachTargetCartridgeId, setAttachTargetCartridgeId] = useState(null);
  const [attachPromptId, setAttachPromptId] = useState('');

  const [promptFormData, setPromptFormData] = useState({
    name: '',
    description: '',
    prompt_text: ''
  });

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    company_name: '',
    industry: 'Healthcare',
    deal_size: '',
    decision_makers: [{ name: '', role: '', persona: 'cfo' }],
    pain_points: [''],
    value_propositions: [''],
    competition: [''],
    timeline: '',
    budget_constraints: '',
    technical_requirements: [''],
    success_metrics: [''],
    prompt_cartridge_id: ''
  });

  const personaOptions = [
    { id: 'cfo', name: 'CFO' },
    { id: 'clinical_director', name: 'Clinical Director' },
    { id: 'it_director', name: 'IT Director' },
    { id: 'ceo', name: 'CEO' }
  ];

  useEffect(() => {
    loadAll();
  }, []);

  const promptById = useMemo(() => {
    const m = {};
    promptCartridges.forEach((p) => {
      m[p.id] = p;
    });
    return m;
  }, [promptCartridges]);

  const loadAll = async () => {
    try {
      setLoading(true);
      await Promise.all([loadCartridges(), loadPromptCartridges()]);
    } finally {
      setLoading(false);
    }
  };

  const loadCartridges = async () => {
    const response = await axios.get('/cartridges');
    setCartridges(response.data.cartridges || []);
  };

  const loadPromptCartridges = async () => {
    try {
      const response = await axios.get('/prompt-cartridges');
      setPromptCartridges(response.data.prompt_cartridges || []);
    } catch (error) {
      // Prompt cartridges are an optional feature; keep the UI usable even if endpoint is missing.
      console.error('Error loading prompt cartridges:', error);
      setPromptCartridges([]);
    }
  };

  const createSampleCartridge = async () => {
    try {
      const response = await axios.post('/cartridges/sample');
      console.log('Sample cartridge created:', response.data.cartridge_id);
      await loadCartridges();
    } catch (error) {
      console.error('Error creating sample cartridge:', error);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        prompt_cartridge_id: formData.prompt_cartridge_id ? formData.prompt_cartridge_id : null,
        decision_makers: formData.decision_makers.filter((dm) => dm.name && dm.role),
        pain_points: formData.pain_points.filter((p) => p.trim()),
        value_propositions: formData.value_propositions.filter((vp) => vp.trim()),
        competition: formData.competition.filter((c) => c.trim()),
        technical_requirements: formData.technical_requirements.filter((tr) => tr.trim()),
        success_metrics: formData.success_metrics.filter((sm) => sm.trim())
      };

      const response = await axios.post('/cartridges', payload);

      console.log('Cartridge created:', response.data.cartridge_id);
      setShowCreateForm(false);
      await loadCartridges();

      if (onCreateCartridge) {
        onCreateCartridge(response.data.cartridge_id);
      }
    } catch (error) {
      console.error('Error creating cartridge:', error);
      alert('Failed to create cartridge. Please try again.');
    }
  };

  const handleCreatePrompt = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: promptFormData.name,
        description: promptFormData.description,
        prompt_text: promptFormData.prompt_text
      };

      const response = await axios.post('/prompt-cartridges', payload);
      console.log('Prompt cartridge created:', response.data.prompt_cartridge_id);

      setShowCreatePromptForm(false);
      setPromptFormData({ name: '', description: '', prompt_text: '' });
      await loadPromptCartridges();
    } catch (error) {
      console.error('Error creating prompt cartridge:', error);
      alert('Failed to create prompt cartridge.');
    }
  };

  const openAttachPrompt = (cartridgeId, currentPromptId) => {
    setAttachTargetCartridgeId(cartridgeId);
    setAttachPromptId(currentPromptId || '');
    setShowAttachPromptForm(true);
  };

  const attachPrompt = async (e) => {
    e.preventDefault();
    if (!attachTargetCartridgeId) return;

    try {
      await axios.put(`/cartridges/${attachTargetCartridgeId}/prompt-cartridge`, {
        prompt_cartridge_id: attachPromptId ? attachPromptId : null
      });
      setShowAttachPromptForm(false);
      setAttachTargetCartridgeId(null);
      setAttachPromptId('');
      await loadCartridges();
    } catch (error) {
      console.error('Error attaching prompt cartridge:', error);
      alert('Failed to attach prompt cartridge.');
    }
  };

  const updateFormField = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const updateArrayField = (field, index, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: prev[field].map((item, i) => (i === index ? value : item))
    }));
  };

  const addArrayItem = (field) => {
    setFormData((prev) => ({
      ...prev,
      [field]: [...prev[field], field === 'decision_makers' ? { name: '', role: '', persona: 'cfo' } : '']
    }));
  };

  const removeArrayItem = (field, index) => {
    setFormData((prev) => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Practice Cartridges</h2>
            <p className="text-sm text-gray-600 mt-1">
              Prompt cartridges: <span className="font-medium">{promptCartridges.length}</span>
            </p>
          </div>
          <div className="space-x-3">
            <button
              onClick={createSampleCartridge}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Create Sample
            </button>
            <button
              onClick={() => setShowCreatePromptForm(true)}
              className="px-4 py-2 bg-slate-700 text-white rounded-md hover:bg-slate-800"
            >
              Create Prompt Cartridge
            </button>
            <button
              onClick={() => setShowCreateForm(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              Create New Cartridge
            </button>
          </div>
        </div>

        {/* Create Prompt Cartridge Modal */}
        {showCreatePromptForm && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-3xl shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Create Prompt Cartridge</h3>

                <form onSubmit={handleCreatePrompt} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Name</label>
                      <input
                        type="text"
                        required
                        value={promptFormData.name}
                        onChange={(e) => setPromptFormData((p) => ({ ...p, name: e.target.value }))}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Description</label>
                      <input
                        type="text"
                        value={promptFormData.description}
                        onChange={(e) => setPromptFormData((p) => ({ ...p, description: e.target.value }))}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">Prompt Instructions</label>
                    <textarea
                      required
                      value={promptFormData.prompt_text}
                      onChange={(e) => setPromptFormData((p) => ({ ...p, prompt_text: e.target.value }))}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      rows="8"
                      placeholder="Example: Always ask 2 discovery questions before presenting a recommendation. Score the user on clarity, specificity, and next steps..."
                    />
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      type="button"
                      onClick={() => setShowCreatePromptForm(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-slate-700 text-white rounded-md hover:bg-slate-800"
                    >
                      Create Prompt
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Attach Prompt Cartridge Modal */}
        {showAttachPromptForm && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-xl shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Attach Prompt Cartridge</h3>

                <form onSubmit={attachPrompt} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Prompt Cartridge</label>
                    <select
                      value={attachPromptId}
                      onChange={(e) => setAttachPromptId(e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                    >
                      <option value="">None (clear)</option>
                      {promptCartridges.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Attach a reusable instruction set to ground the AI behavior across scenarios.
                    </p>
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      type="button"
                      onClick={() => setShowAttachPromptForm(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    >
                      Save
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Create Cartridge Modal */}
        {showCreateForm && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Practice Cartridge</h3>

                <form onSubmit={handleFormSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Cartridge Name</label>
                      <input
                        type="text"
                        required
                        value={formData.name}
                        onChange={(e) => updateFormField('name', e.target.value)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Company Name</label>
                      <input
                        type="text"
                        required
                        value={formData.company_name}
                        onChange={(e) => updateFormField('company_name', e.target.value)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">Description</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => updateFormField('description', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      rows="2"
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Industry</label>
                      <select
                        value={formData.industry}
                        onChange={(e) => updateFormField('industry', e.target.value)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      >
                        <option value="Healthcare">Healthcare</option>
                        <option value="Manufacturing">Manufacturing</option>
                        <option value="Financial Services">Financial Services</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Deal Size</label>
                      <input
                        type="text"
                        value={formData.deal_size}
                        placeholder="e.g., $2.5M"
                        onChange={(e) => updateFormField('deal_size', e.target.value)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Timeline</label>
                      <input
                        type="text"
                        value={formData.timeline}
                        placeholder="e.g., 6 months"
                        onChange={(e) => updateFormField('timeline', e.target.value)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                      />
                    </div>
                  </div>

                  {/* Prompt cartridge selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Prompt Cartridge (optional)</label>
                    <select
                      value={formData.prompt_cartridge_id}
                      onChange={(e) => updateFormField('prompt_cartridge_id', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                    >
                      <option value="">None</option>
                      {promptCartridges.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Prompt cartridges add reusable coaching/evaluation instructions across scenarios.
                    </p>
                  </div>

                  {/* Decision Makers */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Decision Makers</label>
                    {formData.decision_makers.map((dm, index) => (
                      <div key={index} className="grid grid-cols-4 gap-2 mb-2">
                        <input
                          type="text"
                          placeholder="Name"
                          value={dm.name}
                          onChange={(e) => updateArrayField('decision_makers', index, { ...dm, name: e.target.value })}
                          className="border-gray-300 rounded-md shadow-sm"
                        />
                        <input
                          type="text"
                          placeholder="Role"
                          value={dm.role}
                          onChange={(e) => updateArrayField('decision_makers', index, { ...dm, role: e.target.value })}
                          className="border-gray-300 rounded-md shadow-sm"
                        />
                        <select
                          value={dm.persona}
                          onChange={(e) => updateArrayField('decision_makers', index, { ...dm, persona: e.target.value })}
                          className="border-gray-300 rounded-md shadow-sm"
                        >
                          {personaOptions.map((persona) => (
                            <option key={persona.id} value={persona.id}>{persona.name}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => removeArrayItem('decision_makers', index)}
                          className="px-2 py-1 bg-red-500 text-white rounded text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => addArrayItem('decision_makers')}
                      className="px-3 py-1 bg-gray-500 text-white rounded text-sm"
                    >
                      Add Decision Maker
                    </button>
                  </div>

                  {/* Pain Points */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Pain Points</label>
                    {formData.pain_points.map((point, index) => (
                      <div key={index} className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={point}
                          placeholder="Pain point"
                          onChange={(e) => updateArrayField('pain_points', index, e.target.value)}
                          className="flex-1 border-gray-300 rounded-md shadow-sm"
                        />
                        <button
                          type="button"
                          onClick={() => removeArrayItem('pain_points', index)}
                          className="px-2 py-1 bg-red-500 text-white rounded text-sm"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => addArrayItem('pain_points')}
                      className="px-3 py-1 bg-gray-500 text-white rounded text-sm"
                    >
                      Add Pain Point
                    </button>
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      type="button"
                      onClick={() => setShowCreateForm(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    >
                      Create Cartridge
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Cartridge List */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cartridges.length === 0 ? (
            <div className="col-span-full text-center py-8 text-gray-500">
              No cartridges available. Create your first cartridge to get started.
            </div>
          ) : (
            cartridges.map((cartridge) => {
              const promptId = cartridge.prompt_cartridge_id;
              const promptName = promptId ? (promptById[promptId]?.name || 'Prompt attached') : null;

              return (
                <div
                  key={cartridge.id}
                  className="border rounded-lg p-4 hover:shadow-md cursor-pointer transition-shadow"
                  onClick={() => onSelectCartridge(cartridge.id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-lg mb-2">{cartridge.name}</h3>
                      <p className="text-gray-600 text-sm mb-3">{cartridge.description}</p>
                    </div>
                    {promptName && (
                      <span className="text-xs px-2 py-1 bg-slate-100 text-slate-700 rounded">
                        {promptName}
                      </span>
                    )}
                  </div>

                  <div className="flex justify-between items-center text-xs text-gray-500">
                    <span>Created: {new Date(cartridge.created_at).toLocaleDateString()}</span>
                    <span className="px-2 py-1 bg-indigo-100 text-indigo-600 rounded">Practice</span>
                  </div>

                  <div className="mt-3 flex justify-end gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openAttachPrompt(cartridge.id, cartridge.prompt_cartridge_id);
                      }}
                      className="px-3 py-1 text-xs bg-slate-700 text-white rounded hover:bg-slate-800"
                    >
                      Attach Prompt
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default CartridgeSelector;
