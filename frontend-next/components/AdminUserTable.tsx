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

  return (
    <div className="bg-[#f8fafc] p-6 rounded-xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-[#1a202c]">Users</h2>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-[#0073CF] text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#005ba8]"
        >
          + Add User
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#e2e8f0]">
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#718096] uppercase tracking-wide">
                Name
              </th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#718096] uppercase tracking-wide">
                Email
              </th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#718096] uppercase tracking-wide">
                Role
              </th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#718096] uppercase tracking-wide">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-4 text-center text-[#718096]">
                  No users yet.
                </td>
              </tr>
            ) : (
              users.map(user => (
                <tr key={user.id} className="border-b border-[#e2e8f0] hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 text-[#1a202c]">{displayName(user)}</td>
                  <td className="px-4 py-3 text-[#718096]">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className="bg-[#e6f2ff] text-[#0073CF] text-xs font-semibold px-2 py-1 rounded">
                      {user.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 flex gap-2">
                    <button
                      onClick={() => startEdit(user)}
                      className="text-[#0073CF] hover:text-[#005ba8] text-sm font-semibold"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleInvite(user.id)}
                      disabled={inviting === user.id}
                      className="text-[#0073CF] hover:text-[#005ba8] text-sm font-semibold disabled:opacity-50"
                    >
                      {inviting === user.id ? 'Sending…' : 'Invite'}
                    </button>
                    <button
                      onClick={() => setDeleteId(user.id)}
                      className="text-red-600 hover:text-red-700 text-sm font-semibold"
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
          <div className="bg-white rounded-xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold text-[#1a202c] mb-4">Add User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">Work Email</label>
                <input
                  type="email"
                  aria-label="Work Email"
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">First Name</label>
                <input
                  type="text"
                  value={form.first_name}
                  onChange={e => setForm({ ...form, first_name: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">Last Name</label>
                <input
                  type="text"
                  value={form.last_name}
                  onChange={e => setForm({ ...form, last_name: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={e => setForm({ ...form, role: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
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
                className="text-sm font-semibold text-[#718096] px-4 py-2 rounded-lg border border-[#e2e8f0] hover:bg-[#f8fafc]"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={saving}
                className="bg-[#0073CF] text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#005ba8] disabled:opacity-50"
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
          <div className="bg-white rounded-xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold text-[#1a202c] mb-4">Edit User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">First Name</label>
                <input
                  type="text"
                  value={editForm.first_name || ''}
                  onChange={e => setEditForm({ ...editForm, first_name: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">Last Name</label>
                <input
                  type="text"
                  value={editForm.last_name || ''}
                  onChange={e => setEditForm({ ...editForm, last_name: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1a202c] mb-1">Role</label>
                <select
                  value={editForm.role || 'rep'}
                  onChange={e => setEditForm({ ...editForm, role: e.target.value })}
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
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
                className="text-sm font-semibold text-[#718096] px-4 py-2 rounded-lg border border-[#e2e8f0] hover:bg-[#f8fafc]"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={saving}
                className="bg-[#0073CF] text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#005ba8] disabled:opacity-50"
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
          <div className="bg-white rounded-xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold text-[#1a202c] mb-2">Delete User</h3>
            <p className="text-sm text-[#718096] mb-6">
              Are you sure you want to delete this user? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteId(null)}
                className="text-sm font-semibold text-[#718096] px-4 py-2 rounded-lg border border-[#e2e8f0] hover:bg-[#f8fafc]"
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
