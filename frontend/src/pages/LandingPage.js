import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, Zap, Crown, TrendingUp, Shield, Globe, Star,
  CheckCircle, ArrowRight, Bot, Target, MessageCircle,
  BarChart, Users, Calendar, DollarSign, Award
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';

const LandingPage = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className={`fixed w-full z-50 transition-all duration-300 ${
        scrolled ? 'bg-white shadow-lg' : 'bg-transparent'
      }`}>
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <img 
                src="/syroce-logo.svg" 
                alt="Syroce" 
                className={`h-12 transition-all ${scrolled ? '' : 'drop-shadow-lg'}`}
                style={scrolled ? {} : { filter: 'brightness(0) invert(1) drop-shadow(0 0 20px rgba(255,255,255,0.5))' }}
              />
            </div>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className={`font-medium transition ${
                scrolled ? 'text-gray-700 hover:text-blue-600' : 'text-white hover:text-blue-200'
              }`}>Özellikler</a>
              <a href="#ai" className={`font-medium transition ${
                scrolled ? 'text-gray-700 hover:text-blue-600' : 'text-white hover:text-blue-200'
              }`}>AI Teknolojisi</a>
              <a href="#pricing" className={`font-medium transition ${
                scrolled ? 'text-gray-700 hover:text-blue-600' : 'text-white hover:text-blue-200'
              }`}>Çözümler</a>
              <Button 
                onClick={() => navigate('/auth')}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Giriş Yap
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section - Luxury Design */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900"></div>
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0" style={{
            backgroundImage: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.4"%3E%3Cpath d="M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
          }}></div>
        </div>
        
        <div className="relative max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full mb-6 border border-white/20">
              <Sparkles className="w-4 h-4 text-yellow-300" />
              <span className="text-white text-sm font-semibold">Yeni Nesil Otel Yönetim Sistemi</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
              AI-Powered
              <span className="block bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Hotel Management
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-blue-100 mb-8 max-w-3xl mx-auto">
              10 AI Özellik • 865 API Endpoint • 88 Modül • Tam Entegre Çözüm
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button 
                size="lg" 
                onClick={() => navigate('/auth')}
                className="bg-white text-blue-900 hover:bg-blue-50 px-8 py-6 text-lg font-semibold shadow-xl"
              >
                Ücretsiz Demo Başlat
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
              <Button 
                size="lg" 
                variant="outline"
                onClick={() => document.getElementById('ai').scrollIntoView({ behavior: 'smooth' })}
                className="border-2 border-white text-white hover:bg-white/10 px-8 py-6 text-lg font-semibold"
              >
                AI Özellikleri Gör
              </Button>
            </div>
          </div>

          {/* Floating Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-5xl mx-auto">
            {[
              { value: '88', label: 'Modül', icon: <BarChart className="w-6 h-6" /> },
              { value: '865', label: 'API Endpoint', icon: <Zap className="w-6 h-6" /> },
              { value: '<10ms', label: 'Response Time', icon: <Target className="w-6 h-6" /> },
              { value: '10', label: 'Game-Changers', icon: <Crown className="w-6 h-6" /> }
            ].map((stat, idx) => (
              <Card key={idx} className="bg-white/10 backdrop-blur-md border-white/20 hover:bg-white/20 transition">
                <CardContent className="pt-6 text-center">
                  <div className="flex justify-center mb-2">{stat.icon}</div>
                  <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-sm text-blue-200">{stat.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Indicators */}
      <section className="py-12 bg-gray-50 border-y">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-wrap items-center justify-center gap-12 opacity-60">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">550+</div>
              <div className="text-sm text-gray-600">Oda Kapasitesi</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800"><10ms</div>
              <div className="text-sm text-gray-600">Yanıt Süresi</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">%100</div>
              <div className="text-sm text-gray-600">Uptime SLA</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">24/7</div>
              <div className="text-sm text-gray-600">Destek</div>
            </div>
          </div>
        </div>
      </section>

      {/* AI Features - GAME CHANGERS */}
      <section id="ai" className="py-24 bg-gradient-to-br from-purple-50 to-blue-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 rounded-full mb-4">
              <Crown className="w-5 h-5 text-purple-600" />
              <span className="text-purple-900 font-semibold">YENİLİKÇİ TEKNOLOJİLER</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Rakiplerinize Fark Atın
              <span className="block bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                AI Destekli Özellikler
              </span>
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Yapay zeka teknolojileri ile otel yönetiminizi otomatikleştirin
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {[
              {
                icon: <MessageCircle className="w-12 h-12" />,
                title: '🤖 AI WhatsApp Concierge',
                description: '24/7 otomatik misafir hizmeti - Concierge maliyetlerini %50 azaltın',
                roi: 'Tasarruf: €140K/yıl',
                color: 'from-green-500 to-emerald-600'
              },
              {
                icon: <Target className="w-12 h-12" />,
                title: '🔮 Predictive Analytics',
                description: 'No-show ve talep tahminleri - Proaktif kararlar alın',
                roi: 'Gelir Artışı: €300K/yıl',
                color: 'from-purple-500 to-indigo-600'
              },
              {
                icon: <Zap className="w-12 h-12" />,
                title: '⚡ Revenue Autopilot',
                description: 'Otomatik fiyat optimizasyonu - RevPAR\'ınızı artırın',
                roi: 'Gelir Artışı: €500K/yıl',
                color: 'from-orange-500 to-red-600'
              },
              {
                icon: <Star className="w-12 h-12" />,
                title: '📡 Social Media Monitoring',
                description: 'Instagram, Twitter izleme - Kriz yönetimi',
                roi: 'Tasarruf: €230K/yıl',
                color: 'from-pink-500 to-rose-600'
              }
            ].map((feature, idx) => (
              <Card key={idx} className="group hover:shadow-2xl transition-all duration-300 border-2 hover:border-purple-300">
                <CardContent className="p-8">
                  <div className={`inline-flex p-4 rounded-2xl bg-gradient-to-br ${feature.color} mb-4 group-hover:scale-110 transition-transform`}>
                    <div className="text-white">{feature.icon}</div>
                  </div>
                  <h3 className="text-2xl font-bold mb-3 text-gray-900">{feature.title}</h3>
                  <p className="text-gray-600 mb-4">{feature.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-purple-600 bg-purple-100 px-3 py-1 rounded-full">
                      {feature.roi}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Visual Showcase - Dashboard & Mobile */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Modern, Hızlı, Kullanıcı Dostu
            </h2>
            <p className="text-xl text-gray-600">
              Sezgisel arayüz ile ekibiniz hemen adapte olur
            </p>
          </div>

          {/* Dashboard Screenshot Mockup */}
          <div className="mb-16">
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl blur-2xl opacity-20"></div>
              <div className="relative bg-white rounded-2xl shadow-2xl border-4 border-gray-200 p-4">
                <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg p-8 min-h-[400px]">
                  <div className="flex items-center gap-2 mb-6">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  </div>
                  <div className="space-y-4">
                    <div className="h-12 bg-white rounded-lg shadow-sm flex items-center px-4">
                      <div className="w-32 h-4 bg-gradient-to-r from-blue-200 to-purple-200 rounded"></div>
                    </div>
                    <div className="grid grid-cols-4 gap-4">
                      {[1,2,3,4].map(i => (
                        <div key={i} className="h-24 bg-white rounded-lg shadow-sm p-4">
                          <div className="w-full h-full bg-gradient-to-br from-blue-100 to-purple-100 rounded"></div>
                        </div>
                      ))}
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      {[1,2,3].map(i => (
                        <div key={i} className="h-32 bg-white rounded-lg shadow-sm"></div>
                      ))}
                    </div>
                  </div>
                  <div className="text-center mt-8">
                    <span className="text-sm text-gray-500 italic">Dashboard Preview - 6 Kategori, 31 Modül</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Features with Icons */}
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { icon: '⚡', title: 'Ultra Hızlı', desc: '<10ms yanıt süresi' },
              { icon: '🔒', title: 'Güvenli', desc: 'Enterprise-grade security' },
              { icon: '📱', title: 'Mobil', desc: '7 departman mobil app' },
              { icon: '🌍', title: 'Global', desc: '8 dil desteği' }
            ].map((item, idx) => (
              <div key={idx} className="text-center">
                <div className="text-5xl mb-4">{item.icon}</div>
                <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                <p className="text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Core Features */}
      <section id="features" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Enterprise-Grade Özellikler
            </h2>
            <p className="text-xl text-gray-600">
              5 yıldızlı oteller için eksiksiz çözüm
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: <BarChart className="w-10 h-10 text-blue-600" />, title: 'Flash Report', desc: 'Günlük performans 1 dakikada' },
              { icon: <Users className="w-10 h-10 text-green-600" />, title: 'Grup Satış', desc: 'Pickup tracking, master folio' },
              { icon: <Crown className="w-10 h-10 text-purple-600" />, title: 'VIP Management', desc: '3-tier, özel protokoller' },
              { icon: <TrendingUp className="w-10 h-10 text-orange-600" />, title: 'Sales CRM', desc: 'Lead management, funnel' },
              { icon: <Shield className="w-10 h-10 text-red-600" />, title: 'Service Recovery', desc: 'Şikayet + compensation' },
              { icon: <Sparkles className="w-10 h-10 text-pink-600" />, title: 'Spa & Wellness', desc: 'Randevu, treatment, therapist' },
              { icon: <Calendar className="w-10 h-10 text-indigo-600" />, title: 'Meeting & Events', desc: 'BEO generator, catering' },
              { icon: <DollarSign className="w-10 h-10 text-emerald-600" />, title: 'Finance Complete', desc: 'Logo integration, e-fatura' },
              { icon: <Award className="w-10 h-10 text-yellow-600" />, title: 'Advanced Loyalty', desc: 'Gamification, blockchain' }
            ].map((feature, idx) => (
              <div key={idx} className="text-center p-6 rounded-2xl hover:bg-gray-50 transition group">
                <div className="inline-flex p-4 bg-gray-100 rounded-2xl mb-4 group-hover:scale-110 transition">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold mb-2 text-gray-900">{feature.title}</h3>
                <p className="text-gray-600">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof - Department Reviews */}
      <section className="py-20 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4">Tüm Departmanlar İçin Eksiksiz Çözüm</h2>
            <p className="text-xl text-gray-300">Her departman müdürü sistemden tam verim alıyor</p>
          </div>

          <div className="grid md:grid-cols-5 gap-6">
            {[
              { dept: 'Genel Müdür', icon: '👔', benefit: 'Flash Report ile 54 dk/gün tasarruf' },
              { dept: 'Revenue Manager', icon: '💰', benefit: 'AI Pricing ile RevPAR +15%' },
              { dept: 'Satış/Pazarlama', icon: '📊', benefit: 'CRM + Reputation tek ekran' },
              { dept: 'F&B Müdür', icon: '👨‍🍳', benefit: 'Recipe costing + BEO generator' },
              { dept: 'İK Müdür', icon: '👥', benefit: 'Time tracking + Payroll otomatik' }
            ].map((review, idx) => (
              <Card key={idx} className="bg-white/5 border-white/10 hover:bg-white/10 transition">
                <CardContent className="pt-6 text-center">
                  <div className="text-4xl mb-3">{review.icon}</div>
                  <div className="font-semibold mb-2 text-white">{review.dept}</div>
                  <div className="text-sm text-blue-200">{review.benefit}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Fiyatlandırma
            </h2>
            <p className="text-xl text-gray-600">
              ROI 2 ayda geri döner
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { 
                name: 'Starter', 
                price: '€999', 
                period: '/ay', 
                features: ['50 oda', 'Temel PMS', '5 modül', 'Email destek'],
                color: 'border-gray-200'
              },
              { 
                name: 'Professional', 
                price: '€2,499', 
                period: '/ay', 
                popular: true,
                features: ['550 oda', 'Tüm modüller', '31 modül', 'AI özellikleri', '24/7 destek'],
                color: 'border-purple-500 ring-4 ring-purple-100'
              },
              { 
                name: 'Enterprise', 
                price: 'Özel', 
                period: '', 
                features: ['Unlimited', 'Özel geliştirme', 'Multi-property', 'Dedicated support'],
                color: 'border-gray-200'
              }
            ].map((plan, idx) => (
              <Card key={idx} className={`relative ${plan.color} hover:shadow-2xl transition`}>
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                      En Popüler
                    </span>
                  </div>
                )}
                <CardContent className="pt-8 pb-8">
                  <h3 className="text-2xl font-bold text-center mb-4">{plan.name}</h3>
                  <div className="text-center mb-6">
                    <span className="text-5xl font-bold text-gray-900">{plan.price}</span>
                    <span className="text-gray-600">{plan.period}</span>
                  </div>
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-green-600" />
                        <span className="text-gray-700">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button className="w-full" size="lg" variant={plan.popular ? 'default' : 'outline'}>
                    {plan.price === 'Özel' ? 'İletişime Geç' : 'Başla'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-blue-900 to-purple-900 text-white">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Otel Yönetiminizi Bir Sonraki Seviyeye Taşıyın
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Ücretsiz demo ile Syroce'nin gücünü deneyimleyin
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button 
              size="lg" 
              onClick={() => navigate('/auth')}
              className="bg-white text-blue-900 hover:bg-blue-50 px-12 py-6 text-lg font-semibold"
            >
              Ücretsiz Demo Başlat
              <Zap className="w-5 h-5 ml-2" />
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <img src="/syroce-logo.svg" alt="Syroce" className="h-8" />
                <span className="text-xl font-bold text-white">Syroce</span>
              </div>
              <p className="text-sm">Dünyanın en gelişmiş AI-powered hotel PMS'i</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-3">Ürün</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white">Özellikler</a></li>
                <li><a href="#ai" className="hover:text-white">AI Features</a></li>
                <li><a href="#pricing" className="hover:text-white">Fiyatlar</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-3">Şirket</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Hakkımızda</a></li>
                <li><a href="#" className="hover:text-white">Blog</a></li>
                <li><a href="#" className="hover:text-white">Kariyer</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-3">İletişim</h4>
              <ul className="space-y-2 text-sm">
                <li>info@syroce.com</li>
                <li>+90 555 123 45 67</li>
                <li>İstanbul, Türkiye</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm">
            <p>© 2025 Syroce. Tüm hakları saklıdır.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;