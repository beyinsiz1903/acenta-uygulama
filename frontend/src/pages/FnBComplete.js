import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Home, ChefHat, FileText, Package, Monitor } from 'lucide-react';
import { toast } from 'sonner';
import FnBOutletDashboard from '@/components/FnBOutletDashboard';

const FnBComplete = () => {
  const navigate = useNavigate();
  const [recipes, setRecipes] = useState([]);

  useEffect(() => {
    axios.get('/fnb/recipes').then(res => setRecipes(res.data.recipes || [])).catch(() => {});
  }, []);

  return (
    <div className="p-6">
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate('/')}>
            <Home className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">🍳 F&B Management Suite</h1>
            <p className="text-gray-600">Recipe Costing, BEO, Kitchen Display, Inventory</p>
          </div>
        </div>
      </div>

      <Tabs defaultValue="outlet-sales">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="outlet-sales">
            <ChefHat className="w-4 h-4 mr-2" />Outlet Sales
          </TabsTrigger>
          <TabsTrigger value="recipes">
            <ChefHat className="w-4 h-4 mr-2" />Recipes
          </TabsTrigger>
          <TabsTrigger value="beo">
            <FileText className="w-4 h-4 mr-2" />BEO
          </TabsTrigger>
        <TabsContent value="outlet-sales">
          <FnBOutletDashboard />
        </TabsContent>


          <TabsTrigger value="kitchen">
            <Monitor className="w-4 h-4 mr-2" />Kitchen Display
          </TabsTrigger>
          <TabsTrigger value="inventory">
            <Package className="w-4 h-4 mr-2" />Inventory
          </TabsTrigger>
        </TabsList>

        <TabsContent value="recipes">
          <Card>
            <CardHeader><CardTitle>Recipe Costing & Management</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="p-4 bg-green-50 rounded-lg">
                  <p className="font-semibold">Toplam: {recipes.length} recipe</p>
                  <p className="text-sm text-gray-600">Recipe costing sistemi aktif</p>
                </div>
                <Button className="w-full" onClick={() => toast.success('Yeni recipe ekle...')}>
                  + Yeni Recipe Ekle
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="beo">
          <Card>
            <CardHeader><CardTitle>BEO Generator</CardTitle></CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <FileText className="w-16 h-16 text-orange-600 mx-auto mb-4" />
                <p className="text-gray-700 mb-4">Banquet Event Order otomatik oluşturma</p>
                <Button className="bg-orange-600">BEO Oluştur</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="kitchen">
          <Card>
            <CardHeader><CardTitle>Kitchen Display System</CardTitle></CardHeader>
            <CardContent>
              <p className="text-center text-gray-600 py-8">Real-time order display - Mutfak ekranı</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="inventory">
          <Card>
            <CardHeader><CardTitle>Ingredient Inventory</CardTitle></CardHeader>
            <CardContent>
              <p className="text-center text-gray-600 py-8">Malzeme stok takibi, par level, auto reorder</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default FnBComplete;