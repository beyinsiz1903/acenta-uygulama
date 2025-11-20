import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Moon, PlayCircle, CheckCircle, AlertTriangle, Clock, TrendingUp } from 'lucide-react';

const NightAuditModule = () => {
  const [auditStatus, setAuditStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditStatus();
    fetchAuditHistory();
  }, []);

  const fetchAuditStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/night-audit/status`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      const data = await response.json();
      setAuditStatus(data);
    } catch (error) {
      console.error('Error fetching audit status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/night-audit/history?days=30`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      const data = await response.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error('Error fetching audit history:', error);
    }
  };

  const runNightAudit = async () => {
    setRunning(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/night-audit/run`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            audit_date: new Date().toISOString()
          })
        }
      );
      
      if (response.ok) {
        alert('Night audit started successfully!');
        fetchAuditStatus();
        fetchAuditHistory();
      }
    } catch (error) {
      console.error('Error running night audit:', error);
      alert('Failed to run night audit');
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Moon className="w-8 h-8 text-blue-600" />
            Night Audit
          </h1>
          <p className="text-gray-600">Daily closing procedures and date rollover</p>
        </div>
        <Button
          onClick={runNightAudit}
          disabled={running || auditStatus?.status === 'completed'}
          size="lg"
        >
          <PlayCircle className="w-5 h-5 mr-2" />
          {running ? 'Running...' : 'Run Night Audit'}
        </Button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Last Audit</div>
                <div className="text-2xl font-bold">
                  {auditStatus?.last_audit_date || 'N/A'}
                </div>
              </div>
              <Clock className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Status</div>
                <Badge className={auditStatus?.status === 'completed' ? 'bg-green-500' : 'bg-yellow-500'}>
                  {auditStatus?.status || 'Unknown'}
                </Badge>
              </div>
              {auditStatus?.status === 'completed' ? (
                <CheckCircle className="w-8 h-8 text-green-600" />
              ) : (
                <AlertTriangle className="w-8 h-8 text-yellow-600" />
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Next Audit Due</div>
                <div className="text-lg font-bold">
                  {auditStatus?.next_audit_due || 'N/A'}
                </div>
              </div>
              <TrendingUp className="w-8 h-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Pending Tasks</div>
                <div className="text-2xl font-bold">
                  {auditStatus?.pending_tasks?.length || 0}
                </div>
              </div>
              <AlertTriangle className="w-8 h-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Audit Process Steps */}
      <Card>
        <CardHeader>
          <CardTitle>Night Audit Process</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { step: 'Process No-Shows', desc: 'Identify and charge no-show bookings' },
              { step: 'Post Room Revenues', desc: 'Post daily room charges to folios' },
              { step: 'Roll Business Date', desc: 'Advance system date to next day' },
              { step: 'Generate Reports', desc: 'Create daily operational reports' },
              { step: 'Backup Data', desc: 'Create system backup' }
            ].map((item, idx) => (
              <div key={idx} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <div className="font-semibold">{item.step}</div>
                  <div className="text-sm text-gray-600">{item.desc}</div>
                </div>
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Audit History */}
      <Card>
        <CardHeader>
          <CardTitle>Audit History (Last 30 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3">Date</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-right p-3">No-Shows</th>
                  <th className="text-right p-3">Revenues Posted</th>
                  <th className="text-left p-3">Completed At</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 10).map((audit, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="p-3">{audit.audit_date}</td>
                    <td className="p-3">
                      <Badge className="bg-green-500">{audit.status}</Badge>
                    </td>
                    <td className="p-3 text-right">{audit.no_shows}</td>
                    <td className="p-3 text-right">{audit.revenues_posted}</td>
                    <td className="p-3">
                      {new Date(audit.completed_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NightAuditModule;