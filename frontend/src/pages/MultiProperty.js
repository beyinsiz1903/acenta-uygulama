import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent } from '@/components/ui/card';
import { Building } from 'lucide-react';

const MultiProperty = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    axios.get('/multi-property/dashboard').then(res => setData(res.data)).catch(() => {});
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-8">🏢 Multi-Property</h1>
      <Card>
        <CardContent className="pt-8 text-center">
          <Building className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p>Multi-property dashboard hazır</p>
          {data && <p className="text-sm text-gray-500 mt-2">{data.total} otel</p>}
        </CardContent>
      </Card>
    </div>
  );
};

export default MultiProperty;