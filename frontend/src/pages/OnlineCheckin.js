import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Plane, Clock, Hotel, BedDouble, Wind, Coffee, Wifi, 
  MapPin, User, Phone, Mail, CheckCircle2, Sparkles 
} from 'lucide-react';

const OnlineCheckin = () => {
  const { bookingId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1); // 1: Info, 2: Preferences, 3: Upsells, 4: Complete
  const [booking, setBooking] = useState(null);
  const [upsellOffers, setUpsellOffers] = useState([]);
  
  const [formData, setFormData] = useState({
    booking_id: bookingId,
    passport_number: '',
    passport_expiry: '',
    nationality: '',
    estimated_arrival_time: '',
    flight_number: '',
    coming_from: '',
    room_view: 'no_preference',
    floor_preference: 'no_preference',
    bed_type: 'no_preference',
    pillow_type: 'no_preference',
    room_temperature: 22,
    special_requests: '',
    dietary_restrictions: '',
    accessibility_needs: '',
    newspaper_preference: '',
    smoking_preference: false,
    connecting_rooms: false,
    quiet_room: false,
    mobile_number: '',
    whatsapp_number: ''
  });

  useEffect(() => {
    loadBookingDetails();
  }, [bookingId]);

  const loadBookingDetails = async () => {
    try {
      const response = await axios.get(`/bookings/${bookingId}`);
      setBooking(response.data);
    } catch (error) {
      toast.error('Rezervasyon bilgileri yüklenemedi');
    }
  };

  const handleStep1Submit = (e) => {
    e.preventDefault();
    if (!formData.passport_number || !formData.estimated_arrival_time) {
      toast.error('Lütfen zorunlu alanları doldurun');
      return;
    }
    setStep(2);
  };

  const handleStep2Submit = (e) => {
    e.preventDefault();
    setStep(3);
  };

  const handleFinalSubmit = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/checkin/online', formData);
      
      setUpsellOffers(response.data.upsell_offers || []);
      
      if (response.data.upsell_offers && response.data.upsell_offers.length > 0) {
        toast.success('Online check-in tamamlandı! Özel tekliflerinizi inceleyin');
        setStep(3);
      } else {
        toast.success('Online check-in başarıyla tamamlandı!');
        setStep(4);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in başarısız');
    } finally {
      setLoading(false);
    }
  };

  const handleUpsellAction = async (offerId, action) => {
    try {
      await axios.post('/upsell/accept', {
        offer_id: offerId,
        action: action
      });
      
      if (action === 'accept') {
        toast.success('Teklif kabul edildi ve rezervasyonunuza eklendi!');
      }
      
      // Remove offer from list
      setUpsellOffers(upsellOffers.filter(o => o.id !== offerId));
      
      // If no more offers, go to completion
      if (upsellOffers.length === 1) {
        setStep(4);
      }
    } catch (error) {
      toast.error('İşlem başarısız');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <img src="/syroce-logo.svg" alt="Syroce" className="h-16" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Online Check-in
          </h1>
          <p className="text-gray-600">
            Konaklama deneyiminizi başlatmak için birkaç dakikanızı ayırın
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex justify-between items-center max-w-2xl mx-auto">
            {[
              { num: 1, label: 'Bilgiler', icon: User },
              { num: 2, label: 'Tercihler', icon: BedDouble },
              { num: 3, label: 'Teklifler', icon: Sparkles },
              { num: 4, label: 'Tamamlandı', icon: CheckCircle2 }
            ].map((s, idx) => (
              <div key={s.num} className="flex items-center">
                <div className={`flex flex-col items-center ${idx < 3 ? 'flex-1' : ''}`}>
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    step >= s.num 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 text-gray-500'
                  }`}>
                    <s.icon className="w-6 h-6" />
                  </div>
                  <span className="text-xs mt-2 text-gray-600">{s.label}</span>
                </div>
                {idx < 3 && (
                  <div className={`h-1 flex-1 mx-2 ${
                    step > s.num ? 'bg-blue-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step 1: Guest Information */}
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Misafir Bilgileri ve Varış Detayları
              </CardTitle>
              <CardDescription>
                Hızlı check-in için pasaport ve varış bilgilerinizi girin
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleStep1Submit} className="space-y-6">
                {/* Passport Information */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    📄 Pasaport Bilgileri
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>Pasaport Numarası *</Label>
                      <Input
                        value={formData.passport_number}
                        onChange={(e) => setFormData({...formData, passport_number: e.target.value})}
                        placeholder="A12345678"
                        required
                      />
                    </div>
                    <div>
                      <Label>Pasaport Son Kullanma Tarihi</Label>
                      <Input
                        type="date"
                        value={formData.passport_expiry}
                        onChange={(e) => setFormData({...formData, passport_expiry: e.target.value})}
                      />
                    </div>
                    <div>
                      <Label>Uyruk</Label>
                      <Input
                        value={formData.nationality}
                        onChange={(e) => setFormData({...formData, nationality: e.target.value})}
                        placeholder="Türkiye"
                      />
                    </div>
                  </div>
                </div>

                {/* Arrival Details */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Plane className="w-5 h-5" />
                    Varış Detayları
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>Tahmini Varış Saati *</Label>
                      <Input
                        type="time"
                        value={formData.estimated_arrival_time}
                        onChange={(e) => setFormData({...formData, estimated_arrival_time: e.target.value})}
                        required
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Odanızı hazırlayabilmemiz için önemli
                      </p>
                    </div>
                    <div>
                      <Label>Uçuş Numarası</Label>
                      <Input
                        value={formData.flight_number}
                        onChange={(e) => setFormData({...formData, flight_number: e.target.value})}
                        placeholder="TK1234"
                      />
                    </div>
                    <div>
                      <Label>Nereden Geliyorsunuz?</Label>
                      <Input
                        value={formData.coming_from}
                        onChange={(e) => setFormData({...formData, coming_from: e.target.value})}
                        placeholder="İstanbul, Türkiye"
                      />
                    </div>
                  </div>
                </div>

                {/* Contact Info */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Phone className="w-5 h-5" />
                    İletişim Bilgileri
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>Cep Telefonu</Label>
                      <Input
                        type="tel"
                        value={formData.mobile_number}
                        onChange={(e) => setFormData({...formData, mobile_number: e.target.value})}
                        placeholder="+90 555 123 45 67"
                      />
                    </div>
                    <div>
                      <Label>WhatsApp Numarası</Label>
                      <Input
                        type="tel"
                        value={formData.whatsapp_number}
                        onChange={(e) => setFormData({...formData, whatsapp_number: e.target.value})}
                        placeholder="+90 555 123 45 67"
                      />
                    </div>
                  </div>
                </div>

                <Button type="submit" className="w-full" size="lg">
                  Devam Et →
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Room Preferences */}
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BedDouble className="w-5 h-5" />
                Oda Tercihleriniz
              </CardTitle>
              <CardDescription>
                Konfor tercihlerinizi belirleyin, size özel hazırlayalım
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleStep2Submit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Manzara Tercihi</Label>
                    <Select 
                      value={formData.room_view}
                      onValueChange={(val) => setFormData({...formData, room_view: val})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="sea_view">Deniz Manzarası</SelectItem>
                        <SelectItem value="city_view">Şehir Manzarası</SelectItem>
                        <SelectItem value="garden_view">Bahçe Manzarası</SelectItem>
                        <SelectItem value="pool_view">Havuz Manzarası</SelectItem>
                        <SelectItem value="no_preference">Fark Etmez</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Kat Tercihi</Label>
                    <Select 
                      value={formData.floor_preference}
                      onValueChange={(val) => setFormData({...formData, floor_preference: val})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low_floor">Alt Katlar (1-3)</SelectItem>
                        <SelectItem value="middle_floor">Orta Katlar (4-7)</SelectItem>
                        <SelectItem value="high_floor">Üst Katlar (8+)</SelectItem>
                        <SelectItem value="no_preference">Fark Etmez</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Yatak Tipi</Label>
                    <Select 
                      value={formData.bed_type}
                      onValueChange={(val) => setFormData({...formData, bed_type: val})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="king">King Size</SelectItem>
                        <SelectItem value="queen">Queen Size</SelectItem>
                        <SelectItem value="twin">İkiz Yatak</SelectItem>
                        <SelectItem value="no_preference">Fark Etmez</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Yastık Tercihi</Label>
                    <Select 
                      value={formData.pillow_type}
                      onValueChange={(val) => setFormData({...formData, pillow_type: val})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="soft">Yumuşak</SelectItem>
                        <SelectItem value="firm">Sert</SelectItem>
                        <SelectItem value="hypoallergenic">Anti-Alerjik</SelectItem>
                        <SelectItem value="feather">Kaz Tüyü</SelectItem>
                        <SelectItem value="no_preference">Fark Etmez</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Oda Sıcaklığı (°C)</Label>
                    <Input
                      type="number"
                      min="18"
                      max="26"
                      value={formData.room_temperature}
                      onChange={(e) => setFormData({...formData, room_temperature: parseInt(e.target.value)})}
                    />
                  </div>

                  <div>
                    <Label>Gazete Tercihi</Label>
                    <Input
                      value={formData.newspaper_preference}
                      onChange={(e) => setFormData({...formData, newspaper_preference: e.target.value})}
                      placeholder="Hürriyet, Milliyet, vb."
                    />
                  </div>
                </div>

                {/* Special Requests */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Özel İstekler</h3>
                  
                  <div>
                    <Label>Diyet Kısıtlamaları</Label>
                    <Input
                      value={formData.dietary_restrictions}
                      onChange={(e) => setFormData({...formData, dietary_restrictions: e.target.value})}
                      placeholder="Vejetaryen, glutensiz, vegan, vb."
                    />
                  </div>

                  <div>
                    <Label>Erişilebilirlik İhtiyaçları</Label>
                    <Input
                      value={formData.accessibility_needs}
                      onChange={(e) => setFormData({...formData, accessibility_needs: e.target.value})}
                      placeholder="Tekerlekli sandalye erişimi, vb."
                    />
                  </div>

                  <div>
                    <Label>Diğer Özel İstekler</Label>
                    <Textarea
                      value={formData.special_requests}
                      onChange={(e) => setFormData({...formData, special_requests: e.target.value})}
                      placeholder="Sessiz oda, manzaralı oda, üst kat, vb."
                      rows={3}
                    />
                  </div>
                </div>

                {/* Preferences */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="quiet"
                      checked={formData.quiet_room}
                      onCheckedChange={(checked) => setFormData({...formData, quiet_room: checked})}
                    />
                    <Label htmlFor="quiet" className="cursor-pointer">
                      Sessiz oda tercihi (asansör/merdiven uzağı)
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="connecting"
                      checked={formData.connecting_rooms}
                      onCheckedChange={(checked) => setFormData({...formData, connecting_rooms: checked})}
                    />
                    <Label htmlFor="connecting" className="cursor-pointer">
                      Bitişik oda istiyorum
                    </Label>
                  </div>
                </div>

                <div className="flex gap-4">
                  <Button type="button" variant="outline" onClick={() => setStep(1)} className="flex-1">
                    ← Geri
                  </Button>
                  <Button type="button" onClick={handleFinalSubmit} disabled={loading} className="flex-1">
                    {loading ? 'İşleniyor...' : 'Check-in Tamamla'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Upsell Offers */}
        {step === 3 && upsellOffers.length > 0 && (
          <div className="space-y-4">
            <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="w-6 h-6 text-purple-600" />
                  Özel Teklifler - Sadece Sizin İçin!
                </CardTitle>
                <CardDescription>
                  Konaklamanızı daha özel hale getirin
                </CardDescription>
              </CardHeader>
            </Card>

            {upsellOffers.map((offer) => (
              <Card key={offer.id} className="border-2 hover:border-purple-300 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-gray-900 mb-2">
                        {offer.title}
                      </h3>
                      <p className="text-gray-600 mb-4">{offer.description}</p>
                    </div>
                    <div className="text-right ml-4">
                      {offer.discounted_price && (
                        <>
                          <div className="text-sm text-gray-400 line-through">
                            €{offer.original_price}
                          </div>
                          <div className="text-2xl font-bold text-purple-600">
                            €{offer.discounted_price}
                          </div>
                          <div className="text-xs text-green-600 font-semibold">
                            €{offer.savings} tasarruf!
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Button
                      onClick={() => handleUpsellAction(offer.id, 'accept')}
                      className="flex-1 bg-purple-600 hover:bg-purple-700"
                    >
                      ✨ Kabul Et
                    </Button>
                    <Button
                      onClick={() => handleUpsellAction(offer.id, 'reject')}
                      variant="outline"
                      className="flex-1"
                    >
                      İlgilenmiyorum
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}

            <Button 
              onClick={() => setStep(4)} 
              variant="outline" 
              className="w-full"
            >
              Teklifleri Atla →
            </Button>
          </div>
        )}

        {/* Step 4: Completion */}
        {step === 4 && (
          <Card className="border-green-200 bg-green-50">
            <CardContent className="pt-12 pb-12 text-center">
              <CheckCircle2 className="w-20 h-20 text-green-600 mx-auto mb-6" />
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Online Check-in Tamamlandı! 🎉
              </h2>
              <p className="text-lg text-gray-700 mb-6">
                Odanız tercihlerinize göre hazırlanıyor
              </p>
              
              <div className="bg-white rounded-lg p-6 max-w-md mx-auto mb-6">
                <p className="text-sm text-gray-600 mb-2">Express Check-in Kodunuz:</p>
                <div className="text-4xl font-bold text-purple-600 tracking-wider">
                  ••••••
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Bu kod e-postanıza gönderildi
                </p>
              </div>

              <div className="space-y-3 text-left max-w-md mx-auto">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">Resepsiyona geldiğinizde</p>
                    <p className="text-sm text-gray-600">Sadece kimliğinizi gösterin, odanız hazır!</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">Check-in saati: 14:00</p>
                    <p className="text-sm text-gray-600">Erken varışta bavullarınızı emanet edebilirsiniz</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">Tercihleriniz kaydedildi</p>
                    <p className="text-sm text-gray-600">Odanız isteklerinize göre hazırlanacak</p>
                  </div>
                </div>
              </div>

              <Button onClick={() => navigate('/')} className="mt-8" size="lg">
                Ana Sayfaya Dön
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default OnlineCheckin;
