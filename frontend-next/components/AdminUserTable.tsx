'use client'

import { useState } from 'react'

export interface AdminUser {
  id: string
  email: string
  first_name: string | null
  last_name: string | null
  role: string
  cohort_id: string | null
}

interface Props {
  users: AdminUser[]
  onAdd: (data: { email: string; first_name: string; last_name: string; role: string }) => Promise<void>
  onUpdate: (id: string, data: Partial<AdminUser>) => Promise<void>
  onDelete: (id: string) => Promise<void>
  onInvite: (id: string) => Promise<void>
}

export default function AdminUserTable({ users, onAdd, onUpdate, onDelete, onInvite }: Props) {
  const [showAdd, setShowAdd] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [inviting, setInviting] = useState<string | null>(null)
  const [form, setForm] = useState({ email: '', first_name: '', last_name: '', role: 'rep' })
  const [editForm, setEditForm] = useState<Partial<AdminUser> | null>(null)

  async function handleAdd() {
    try {
      setSaving(true)
      await onAdd(form)
      setForm({ email: '', first_name: '', last_name: '', role: 'rep' })
      setShowAdd(false)
    } finally {
      setSaving(false)
    }
  }

  function startEdit(user: AdminUser) {
    setEditId(user.id)
    setEditForm({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      role: user.role,
    })
  }

  async function handleUpdate() {
    if (!editId || !editForm) return
    try {
      setSaving(true)
      await onUpdate(editId, editForm)
      setEditId(null)
      setEditForm(null)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    try {
      setSaving(true)
      await onDelete(deleteId)
      setDeleteId(null)
    } finally {
      setSaving(false)
    }
  }

  async function handleInvite(id: string) {
    try {
      setInviting(id)
      await onInvite(id)
    } finally {
      setInviting(null)
    }
  }

  const displayName = (user: AdminUser) => {
    const parts = [user.first_name, user.last_name].filter(Boolean)
    return parts.length > 0 ? parts.join(' ') : '—'
  }

  const inputClass = 'rounded-lg px-3 py-2 text-sm w-full bg-[#181c22] text-[#e8eaed] focus:outline-none focus:border-[#2ddbde] focus:ring-2 focus:ring-[#2ddbde]/30'

  return (
    <div className="bg-[#10141a] p-6 rounded-xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-[#e8eaed]">Users</h2>
        <button
          onClick={() => setShowAdd(true)}
          className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          + Add User
        </button>
      </div>

      {/* Table */}
      <div className="bg-[#1c2026] rounded-xl overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#9aa0a6] uppercase tracking-wide">
                Name
              </th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#9aa0a6] uppercase tracking-wide">
                Email
              </th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#9aa0a6] uppercase tracking-wide">
                Role
              </th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#9aa0a6] uppercase tracking-wide">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-4 text-center text-[#9aa0a6]">
                  No users yet.
                </td>
              </tr>
            ) : (
              users.map(user => (
                <tr key={user.id} className="hover:bg-[#353940] transition-colors" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <td className="px-4 py-3 text-[#e8eaed]">{displayName(user)}</td>
                  <td className="px-4 py-3 text-[#9aa0a6]">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className="bg-[#2ddbde]/15 text-[#2ddbde] text-xs font-semibold px-2 py-1 rounded">
                      {user.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 flex gap-2">
                    <button
                      onClick={() => startEdit(user)}
                      className="text-[#2ddbde] hover:text-[#2ddbde]/80 text-sm font-semibold"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleInvite(user.id)}
                      disabled={inviting === user.id}
                      className="text-[#2ddbde] hover:text-[#2ddbde]/80 text-sm font-semibold disabled:opacity-50"
                    >
                      {inviting === user.id ? 'Sending…' : 'Invite'}
                    </button>
                    <button
                      onClick={() => setDeleteId(user.id)}
                      className="text-red-500 hover:text-red-400 text-sm font-semibold"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1c2026] rounded-xl p-6 w-full max-w-sm" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            <h3 className="text-lg font-semibold text-[#e8eaed] mb-4">Add User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">Work Email</label>
                <input
                  type="email"
                  aria-label="Work Email"
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">First Name</label>
                <input
                  type="text"
                  value={form.first_name}
                  onChange={e => setForm({ ...form, first_name: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">Last Name</label>
                <input
                  type="text"
                  value={form.last_name}
                  onChange={e => setForm({ ...form, last_name: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={e => setForm({ ...form, role: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  <option value="rep">Rep</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 justify-end mt-6">
              <button
                onClick={() => setShowAdd(false)}
                className="text-sm font-semibold text-[#9aa0a6] px-4 py-2 rounded-lg hover:bg-[#353940]"
                style={{ border: '1px solid rgba(255,255,255,0.08)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={saving}
                className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
              >
                Add & Invite
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editId && editForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1c2026] rounded-xl p-6 w-full max-w-sm" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            <h3 className="text-lg font-semibold text-[#e8eaed] mb-4">Edit User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">First Name</label>
                <input
                  type="text"
                  value={editForm.first_name || ''}
                  onChange={e => setEditForm({ ...editForm, first_name: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">Last Name</label>
                <input
                  type="text"
                  value={editForm.last_name || ''}
                  onChange={e => setEditForm({ ...editForm, last_name: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#e8eaed] mb-1">Role</label>
                <select
                  value={editForm.role || 'rep'}
                  onChange={e => setEditForm({ ...editForm, role: e.target.value })}
                  className={inputClass}
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  <option value="rep">Rep</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 justify-end mt-6">
              <button
                onClick={() => {
                  setEditId(null)
                  setEditForm(null)
                }}
                className="text-sm font-semibold text-[#9aa0a6] px-4 py-2 rounded-lg hover:bg-[#353940]"
                style={{ border: '1px solid rgba(255,255,255,0.08)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={saving}
                className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1c2026] rounded-xl p-6 w-full max-w-sm" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            <h3 className="text-lg font-semibold text-[#e8eaed] mb-2">Delete User</h3>
            <p className="text-sm text-[#9aa0a6] mb-6">
              Are you sure you want to delete this user? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteId(null)}
                className="text-sm font-semibold text-[#9aa0a6] px-4 py-2 rounded-lg hover:bg-[#353940]"
                style={{ border: '1px solid rgba(255,255,255,0.08)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={saving}
                className="bg-red-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
