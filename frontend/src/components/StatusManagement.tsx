import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Save, X } from 'lucide-react';
import client from '../api/client';

interface Status {
  id: number;
  name: string;
  color: string;
  is_closed: boolean;
  display_order: number;
}

const StatusManagement: React.FC = () => {
  const [statuses, setStatuses] = useState<Status[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<Status>>({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [newStatus, setNewStatus] = useState({ name: '', color: 'gray', is_closed: false, display_order: 0 });
  const [error, setError] = useState<string | null>(null);

  const colorOptions = [
    { value: 'gray', label: 'Gray', class: 'bg-gray-100 text-gray-800' },
    { value: 'blue', label: 'Blue', class: 'bg-blue-100 text-blue-800' },
    { value: 'green', label: 'Green', class: 'bg-green-100 text-green-800' },
    { value: 'yellow', label: 'Yellow', class: 'bg-yellow-100 text-yellow-800' },
    { value: 'orange', label: 'Orange', class: 'bg-orange-100 text-orange-800' },
    { value: 'red', label: 'Red', class: 'bg-red-100 text-red-800' },
    { value: 'purple', label: 'Purple', class: 'bg-purple-100 text-purple-800' },
    { value: 'pink', label: 'Pink', class: 'bg-pink-100 text-pink-800' },
  ];

  useEffect(() => {
    loadStatuses();
  }, []);

  const loadStatuses = async () => {
    try {
      setLoading(true);
      const response = await client.get('/api/statuses');
      setStatuses(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load statuses');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    try {
      setError(null);
      await client.post('/api/statuses', newStatus);
      setNewStatus({ name: '', color: 'gray', is_closed: false, display_order: 0 });
      setShowAddForm(false);
      loadStatuses();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create status');
    }
  };

  const handleEdit = (status: Status) => {
    setEditingId(status.id);
    setEditForm(status);
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;
    try {
      setError(null);
      await client.put(`/api/statuses/${editingId}`, editForm);
      setEditingId(null);
      setEditForm({});
      loadStatuses();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this status? This will fail if any tickets are using it.')) return;
    try {
      setError(null);
      await client.delete(`/api/statuses/${id}`);
      loadStatuses();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete status');
    }
  };

  const getColorClass = (color: string) => {
    return colorOptions.find(c => c.value === color)?.class || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return <div className="p-4">Loading statuses...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Custom Statuses</h3>
          <p className="text-sm text-gray-500">Manage ticket statuses independent from the old system</p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Add Status
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Add Form */}
      {showAddForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">New Status</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={newStatus.name}
                onChange={(e) => setNewStatus({ ...newStatus, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Status name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
              <select
                value={newStatus.color}
                onChange={(e) => setNewStatus({ ...newStatus, color: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                {colorOptions.map(color => (
                  <option key={color.value} value={color.value}>{color.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Display Order</label>
              <input
                type="number"
                value={newStatus.display_order}
                onChange={(e) => setNewStatus({ ...newStatus, display_order: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div className="flex items-center">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newStatus.is_closed}
                  onChange={(e) => setNewStatus({ ...newStatus, is_closed: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Mark as closed status</span>
              </label>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Create
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Status List */}
      <div className="space-y-2">
        {statuses.map((status) => (
          <div
            key={status.id}
            className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between"
          >
            {editingId === status.id ? (
              // Edit mode
              <div className="flex-1 grid grid-cols-4 gap-4">
                <input
                  type="text"
                  value={editForm.name || ''}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md"
                />
                <select
                  value={editForm.color || 'gray'}
                  onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md"
                >
                  {colorOptions.map(color => (
                    <option key={color.value} value={color.value}>{color.label}</option>
                  ))}
                </select>
                <input
                  type="number"
                  value={editForm.display_order || 0}
                  onChange={(e) => setEditForm({ ...editForm, display_order: parseInt(e.target.value) })}
                  className="px-3 py-2 border border-gray-300 rounded-md"
                />
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editForm.is_closed || false}
                    onChange={(e) => setEditForm({ ...editForm, is_closed: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Closed</span>
                </label>
              </div>
            ) : (
              // View mode
              <div className="flex-1 flex items-center gap-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getColorClass(status.color)}`}>
                  {status.name}
                </span>
                <span className="text-sm text-gray-500">Order: {status.display_order}</span>
                {status.is_closed && (
                  <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">CLOSED</span>
                )}
              </div>
            )}

            <div className="flex gap-2">
              {editingId === status.id ? (
                <>
                  <button
                    onClick={handleSaveEdit}
                    className="p-2 text-green-600 hover:bg-green-50 rounded"
                  >
                    <Save className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      setEditingId(null);
                      setEditForm({});
                    }}
                    className="p-2 text-gray-600 hover:bg-gray-50 rounded"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => handleEdit(status)}
                    className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(status.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default StatusManagement;
