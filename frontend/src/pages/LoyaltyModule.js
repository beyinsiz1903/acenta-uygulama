import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Award, Plus, TrendingUp, TrendingDown, Star } from 'lucide-react';

const LoyaltyModule = ({ user, tenant, onLogout }) => {
  const [programs, setPrograms] = useState([]);
  const [guests, setGuests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(null);
  const [selectedGuest, setSelectedGuest] = useState(null);

  const [newTransaction, setNewTransaction] = useState({
    guest_id: '',
    points: 0,
    transaction_type: 'earned',
    description: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [programsRes, guestsRes] = await Promise.all([
        axios.get('/loyalty/programs'),
        axios.get('/pms/guests')
      ]);
      setPrograms(programsRes.data);
      setGuests(guestsRes.data);
    } catch (error) {
      toast.error('Failed to load loyalty data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTransaction = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/loyalty/transactions', newTransaction);
      toast.success('Points transaction successful');
      setOpenDialog(null);
      loadData();
      setNewTransaction({ guest_id: '', points: 0, transaction_type: 'earned', description: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create transaction');
    }
  };

  const createLoyaltyProgram = async (guestId) => {
    try {
      await axios.post('/loyalty/programs', {
        guest_id: guestId,
        tier: 'bronze',
        points: 0,
        lifetime_points: 0
      });
      toast.success('Loyalty program created');
      loadData();
    } catch (error) {
      toast.error('Failed to create loyalty program');
    }
  };

  const getTierColor = (tier) => {
    switch(tier) {
      case 'platinum': return 'bg-purple-100 text-purple-700';
      case 'gold': return 'bg-yellow-100 text-yellow-700';
      case 'silver': return 'bg-gray-100 text-gray-700';
      default: return 'bg-orange-100 text-orange-700';
    }
  };

  const getTierIcon = (tier) => {
    const count = tier === 'platinum' ? 4 : tier === 'gold' ? 3 : tier === 'silver' ? 2 : 1;
    return Array(count).fill(0).map((_, i) => <Star key={i} className="w-3 h-3 fill-current" />);
  };

  if (loading) {
    return (
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="loyalty">
        <div className="p-6 text-center">Loading...</div>
      </Layout>
    );
  }

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="loyalty">
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>Guest Loyalty Program</h1>
            <p className="text-gray-600">Reward your loyal guests and track their benefits</p>
          </div>
          <Dialog open={openDialog === 'transaction'} onOpenChange={(open) => setOpenDialog(open ? 'transaction' : null)}>
            <DialogTrigger asChild>
              <Button data-testid="add-points-btn">
                <Plus className="w-4 h-4 mr-2" />
                Add Points
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Points Transaction</DialogTitle>
                <DialogDescription>Award or redeem loyalty points</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateTransaction} className="space-y-4">
                <div>
                  <Label htmlFor="transaction-guest">Guest</Label>
                  <Select value={newTransaction.guest_id} onValueChange={(v) => setNewTransaction({...newTransaction, guest_id: v})}>
                    <SelectTrigger id="transaction-guest" data-testid="transaction-guest-select">
                      <SelectValue placeholder="Select guest" />
                    </SelectTrigger>
                    <SelectContent>
                      {guests.map(g => (
                        <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="transaction-type">Type</Label>
                  <Select value={newTransaction.transaction_type} onValueChange={(v) => setNewTransaction({...newTransaction, transaction_type: v})}>
                    <SelectTrigger id="transaction-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="earned">Earned</SelectItem>
                      <SelectItem value="redeemed">Redeemed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="points">Points</Label>
                  <Input
                    id="points"
                    type="number"
                    value={newTransaction.points}
                    onChange={(e) => setNewTransaction({...newTransaction, points: parseInt(e.target.value)})}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={newTransaction.description}
                    onChange={(e) => setNewTransaction({...newTransaction, description: e.target.value})}
                    required
                  />
                </div>
                <Button type="submit" className="w-full" data-testid="submit-transaction-btn">Submit Transaction</Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Loyalty Programs */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {programs.map((program) => {
            const guest = guests.find(g => g.id === program.guest_id);
            return (
              <Card key={program.id} data-testid={`loyalty-card-${program.guest_id}`}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle>{guest?.name || 'Unknown Guest'}</CardTitle>
                      <p className="text-sm text-gray-600">{guest?.email}</p>
                    </div>
                    <Award className="w-6 h-6 text-blue-500" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Tier</span>
                    <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getTierColor(program.tier)}`}>
                      {getTierIcon(program.tier)}
                      <span className="ml-1 capitalize">{program.tier}</span>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t">
                    <div className="text-center">
                      <div className="text-4xl font-bold text-blue-600">{program.points}</div>
                      <div className="text-sm text-gray-600 mt-1">Available Points</div>
                    </div>
                  </div>

                  <div className="pt-2 border-t text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Lifetime Points</span>
                      <span className="font-medium">{program.lifetime_points}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Guests without loyalty program */}
        <div>
          <h2 className="text-2xl font-semibold mb-4">Guests Without Loyalty Program</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {guests
              .filter(g => !programs.find(p => p.guest_id === g.id))
              .map((guest) => (
                <Card key={guest.id}>
                  <CardContent className="pt-6">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-semibold">{guest.name}</p>
                        <p className="text-sm text-gray-600">{guest.email}</p>
                      </div>
                      <Button 
                        size="sm" 
                        onClick={() => createLoyaltyProgram(guest.id)}
                        data-testid={`enroll-guest-${guest.id}`}
                      >
                        Enroll
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
          </div>
        </div>

        {programs.length === 0 && guests.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center text-gray-500">
              <p>No guests found. Add guests in the PMS module first.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

export default LoyaltyModule;
