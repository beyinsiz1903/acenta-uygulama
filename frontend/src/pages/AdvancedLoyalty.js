import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Gift, Star, Award } from 'lucide-react';

const AdvancedLoyalty = () => {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-8">🎯 Advanced Loyalty</h1>
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <Award className="w-12 h-12 text-yellow-600 mx-auto mb-2" />
            <p className="text-2xl font-bold">Gold</p>
            <p className="text-sm text-gray-500">Tier</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Star className="w-12 h-12 text-purple-600 mx-auto mb-2" />
            <p className="text-2xl font-bold">2,500</p>
            <p className="text-sm text-gray-500">Puan</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Gift className="w-12 h-12 text-green-600 mx-auto mb-2" />
            <p className="text-2xl font-bold">5</p>
            <p className="text-sm text-gray-500">Hediye</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdvancedLoyalty;