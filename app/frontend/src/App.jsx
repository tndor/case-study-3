import React, { useState, useEffect } from 'react';
import { Users, UserPlus, UserMinus, Terminal, Activity, CheckCircle, AlertCircle } from 'lucide-react';

// NOTE: In a real K8s deployment, this URL comes from an environment variable pointing to the Backend Service
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [employees, setEmployees] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    department: 'Engineering',
    role: 'Developer'
  });

  const fetchEmployees = async () => {
    try {
      const res = await fetch(`${API_URL}/employees`);
      const data = await res.json();
      setEmployees(data);
    } catch (err) {
      console.error("Failed to fetch employees", err);
      // Fallback mock data for UI preview if backend isn't running
      setEmployees([
        { id: '1', username: 'jane.doe', status: 'Active', department: 'Engineering' },
        { id: '2', username: 'bob.smith', status: 'Provisioning', department: 'Sales' }
      ]);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const addLog = (message, type = 'info') => {
    setLogs(prev => [{ time: new Date().toLocaleTimeString(), message, type }, ...prev]);
  };

  const handleOnboard = async (e) => {
    e.preventDefault();
    setLoading(true);
    addLog(`Starting onboarding workflow for ${formData.firstName} ${formData.lastName}...`, 'info');

    try {
      const response = await fetch(`${API_URL}/onboard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      const result = await response.json();
      
      if (response.ok) {
        addLog(`SUCCESS: ${result.message}`, 'success');
        // Log specific provisioning steps returned by backend
        result.steps.forEach(step => addLog(`WORKFLOW: ${step}`, 'success'));
        fetchEmployees();
        setFormData({ firstName: '', lastName: '', department: 'Engineering', role: 'Developer' });
      } else {
        addLog(`ERROR: ${result.error}`, 'error');
      }
    } catch (err) {
      addLog(`NETWORK ERROR: Is the backend running?`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleOffboard = async (username) => {
    if (!confirm(`Are you sure you want to terminate ${username}? This will delete IAM users and revoke access.`)) return;
    
    setLoading(true);
    addLog(`Initiating offboarding sequence for ${username}...`, 'warning');

    try {
      const response = await fetch(`${API_URL}/offboard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });
      const result = await response.json();
      
      if (response.ok) {
        addLog(`TERMINATION COMPLETE: ${username} deactivated.`, 'success');
        fetchEmployees();
      } else {
        addLog(`ERROR: ${result.error}`, 'error');
      }
    } catch (err) {
      addLog(`Failed to connect to backend`, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Navbar */}
      <nav className="bg-indigo-600 text-white p-4 shadow-lg">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-6 w-6" />
            <span className="text-xl font-bold tracking-tight">Innovatech HR Automator</span>
          </div>
          <div className="text-sm bg-indigo-700 px-3 py-1 rounded-full">
            Kubernetes Cluster: <span className="text-green-300">Connected</span>
          </div>
        </div>
      </nav>

      <div className="container mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Controls */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Tabs */}
          <div className="bg-white rounded-xl shadow-sm p-1 flex space-x-1 border border-slate-200">
            <button 
              onClick={() => setActiveTab('dashboard')}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${activeTab === 'dashboard' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              <div className="flex items-center justify-center space-x-2">
                <Users size={18} /> <span>Employee List</span>
              </div>
            </button>
            <button 
              onClick={() => setActiveTab('onboard')}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${activeTab === 'onboard' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              <div className="flex items-center justify-center space-x-2">
                <UserPlus size={18} /> <span>New Hire Provisioning</span>
              </div>
            </button>
          </div>

          {/* Content Area */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 min-h-[400px] p-6">
            
            {activeTab === 'dashboard' && (
              <div>
                <h2 className="text-lg font-semibold mb-4">Active Directory & Cloud Accounts</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 uppercase border-b">
                      <tr>
                        <th className="px-4 py-3">Username</th>
                        <th className="px-4 py-3">Role</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {employees.map((emp) => (
                        <tr key={emp.id || emp.username} className="hover:bg-slate-50 transition">
                          <td className="px-4 py-3 font-medium text-slate-800">{emp.username}</td>
                          <td className="px-4 py-3 text-slate-500">{emp.department}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${emp.status === 'Active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                              {emp.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button 
                              onClick={() => handleOffboard(emp.username)}
                              className="text-red-600 hover:text-red-800 hover:bg-red-50 p-2 rounded transition"
                              title="Terminate & Deprovision"
                            >
                              <UserMinus size={18} />
                            </button>
                          </td>
                        </tr>
                      ))}
                      {employees.length === 0 && (
                        <tr>
                          <td colSpan="4" className="text-center py-8 text-slate-400">No employees found in Database.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'onboard' && (
              <div className="max-w-lg mx-auto">
                <h2 className="text-lg font-semibold mb-2">Provision New Employee</h2>
                <p className="text-sm text-slate-500 mb-6">
                  This action triggers the backend to create an AWS IAM User, generate access keys, and create a personal S3 Home Folder.
                </p>
                
                <form onSubmit={handleOnboard} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">First Name</label>
                      <input 
                        required
                        name="firstName" 
                        value={formData.firstName}
                        onChange={handleInputChange}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none" 
                        placeholder="Jane"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Last Name</label>
                      <input 
                        required
                        name="lastName" 
                        value={formData.lastName}
                        onChange={handleInputChange}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none" 
                        placeholder="Doe"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Department</label>
                    <select 
                      name="department"
                      value={formData.department}
                      onChange={handleInputChange}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                    >
                      <option>Engineering</option>
                      <option>Sales</option>
                      <option>HR</option>
                      <option>Executive</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Role Policy</label>
                    <select 
                      name="role"
                      value={formData.role}
                      onChange={handleInputChange}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                    >
                      <option>Developer (S3 + EC2 Access)</option>
                      <option>Analyst (Read Only)</option>
                      <option>Admin (Full Access)</option>
                    </select>
                  </div>

                  <button 
                    disabled={loading}
                    type="submit" 
                    className={`w-full flex items-center justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white ${loading ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                  >
                    {loading ? (
                      <>Processing Workflow...</>
                    ) : (
                      <>
                        <UserPlus className="mr-2 h-5 w-5" /> Confirm & Provision
                      </>
                    )}
                  </button>
                </form>
              </div>
            )}

          </div>
        </div>

        {/* Right Column: Provisioning Logs */}
        <div className="bg-slate-900 text-slate-200 rounded-xl shadow-lg p-4 overflow-hidden flex flex-col max-h-[600px]">
          <div className="flex items-center justify-between mb-4 border-b border-slate-700 pb-2">
            <div className="flex items-center space-x-2">
              <Terminal size={18} className="text-indigo-400" />
              <span className="font-mono text-sm font-bold">Workflow Logs</span>
            </div>
            <button onClick={() => setLogs([])} className="text-xs text-slate-500 hover:text-white">Clear</button>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs">
            {logs.length === 0 && <div className="text-slate-600 italic">Waiting for system events...</div>}
            {logs.map((log, i) => (
              <div key={i} className="flex space-x-2">
                <span className="text-slate-500">[{log.time}]</span>
                <span className={
                  log.type === 'error' ? 'text-red-400' : 
                  log.type === 'success' ? 'text-green-400' : 
                  log.type === 'warning' ? 'text-yellow-400' : 'text-slate-300'
                }>
                  {log.type === 'success' && <CheckCircle size={10} className="inline mr-1" />}
                  {log.type === 'error' && <AlertCircle size={10} className="inline mr-1" />}
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}