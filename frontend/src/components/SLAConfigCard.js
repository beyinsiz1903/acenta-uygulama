import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, AlertCircle } from 'lucide-react';

const SLAConfigCard = ({ slaConfigs, delayedTasks }) => {
  const getCategoryName = (category) => {
    const names = {
      'maintenance': 'Bakım',
      'housekeeping': 'Temizlik',
      'guest_request': 'Misafir Talepleri'
    };
    return names[category] || category;
  };

  const getPriorityColor = (priority) => {
    const colors = {
      'urgent': 'bg-red-500',
      'high': 'bg-orange-500',
      'normal': 'bg-blue-500',
      'low': 'bg-gray-500'
    };
    return colors[priority] || 'bg-gray-500';
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>SLA Hedefleri</span>
            {delayedTasks && delayedTasks.length > 0 && (
              <Badge className="bg-red-500">
                {delayedTasks.length} Gecikmiş
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {slaConfigs && slaConfigs.length > 0 ? (
              slaConfigs.map((config, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${getPriorityColor(config.priority)}`} />
                    <div>
                      <p className="font-medium text-sm">{getCategoryName(config.category)}</p>
                      <p className="text-xs text-gray-500 capitalize">{config.priority}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{config.response_time_minutes} dk → {config.resolution_time_minutes} dk</p>
                    <p className="text-xs text-gray-500">Yanıt → Çözüm</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-gray-500 text-sm">
                <Clock className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                Varsayılan SLA kullanılıyor
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {delayedTasks && delayedTasks.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-800">
              <AlertCircle className="w-5 h-5" />
              Geciken Görevler
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {delayedTasks.slice(0, 5).map((task) => (
                <div key={task.id} className="p-3 bg-white rounded border border-red-200">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">Oda {task.room_number}</span>
                    <Badge className="bg-red-500 text-xs">{task.delay_minutes} dk gecikme</Badge>
                  </div>
                  <p className="text-xs text-gray-600">{task.guest_name}</p>
                  <p className="text-xs text-gray-500 mt-1">SLA: {task.sla_minutes} dk | Geçen: {task.elapsed_minutes} dk</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SLAConfigCard;