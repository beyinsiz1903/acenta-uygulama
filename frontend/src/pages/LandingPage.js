import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Hotel, 
  TrendingUp, 
  Users, 
  Calendar, 
  DollarSign, 
  BarChart3, 
  Smartphone,
  CheckCircle,
  ArrowRight,
  Zap,
  Shield,
  Globe
} from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();
  const [demoForm, setDemoForm] = useState({
    name: '',
    email: '',
    phone: '',
    hotelName: '',
    roomCount: ''
  });
  const [submitStatus, setSubmitStatus] = useState('');

  const handleDemoRequest = async (e) => {
    e.preventDefault();
    setSubmitStatus('sending');
    
    try {
      // Backend'e demo request gönder
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/demo-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(demoForm)
      });
      
      if (response.ok) {
        setSubmitStatus('success');
        setDemoForm({ name: '', email: '', phone: '', hotelName: '', roomCount: '' });
      } else {
        setSubmitStatus('error');
      }
    } catch (error) {
      setSubmitStatus('error');
    }
  };

  const features = [
    {
      icon: <Hotel className="w-8 h-8" />,
      title: "Kapsamlı Rezervasyon Yönetimi",
      description: "Online kanallar, OTA entegrasyonları ve doğrudan rezervasyonları tek platformdan yönetin"
    },
    {
      icon: <TrendingUp className="w-8 h-8" />,
      title: "Gelir Yönetimi (RMS)",
      description: "AI destekli dinamik fiyatlandırma ve tahmine dayalı analizlerle gelirinizi maksimize edin"
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: "360° Misafir Profili",
      description: "Tercihleri, geçmiş rezervasyonları ve sadakat puanları ile tam misafir yönetimi"
    },
    {
      icon: <Calendar className="w-8 h-8" />,
      title: "Kat Hizmetleri",
      description: "Oda durumu, temizlik görevleri ve bakım planlaması için mobil uygulama"
    },
    {
      icon: <DollarSign className="w-8 h-8" />,
      title: "Folio & Muhasebe",
      description: "Otomatik fatura oluşturma, ödeme takibi ve detaylı mali raporlama"
    },
    {
      icon: <BarChart3 className="w-8 h-8" />,
      title: "İleri Analitik & Raporlar",
      description: "Gerçek zamanlı KPI'lar, performans metrikleri ve özelleştirilebilir dashboard'lar"
    },
    {
      icon: <Smartphone className="w-8 h-8" />,
      title: "Mobil Uygulamalar",
      description: "GM, Front Desk, Housekeeping ve F&B için özel mobil uygulamalar"
    },
    {
      icon: <Globe className="w-8 h-8" />,
      title: "Çoklu Dil & Para Birimi",
      description: "8 dil desteği ve tüm önemli para birimleri ile global operasyon"
    }
  ];

  const stats = [
    { value: "500+", label: "Aktif Otel" },
    { value: "50K+", label: "Aylık Rezervasyon" },
    { value: "%98", label: "Müşteri Memnuniyeti" },
    { value: "24/7", label: "Canlı Destek" }
  ];

  const pricingPlans = [
    {
      name: "Başlangıç",
      price: "€99",
      period: "/ay",
      features: [
        "50 odaya kadar",
        "Temel rezervasyon yönetimi",
        "Kat hizmetleri modülü",
        "Email destek",
        "Mobil erişim"
      ]
    },
    {
      name: "Profesyonel",
      price: "€299",
      period: "/ay",
      popular: true,
      features: [
        "200 odaya kadar",
        "Gelir yönetimi (RMS)",
        "OTA entegrasyonları",
        "Channel Manager",
        "7/24 destek",
        "Mobil uygulamalar",
        "Özel raporlar"
      ]
    },
    {
      name: "Kurumsal",
      price: "Özel",
      period: "fiyat",
      features: [
        "Sınırsız oda",
        "Tüm modüller",
        "Çoklu otel yönetimi",
        "API erişimi",
        "Özel geliştirmeler",
        "Dedicated support",
        "On-premise seçeneği"
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header/Navigation */}
      <nav className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <Hotel className="w-8 h-8 text-blue-600" />
              <span className="text-2xl font-bold text-gray-900">RoomOps PMS</span>
            </div>
            <div className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-gray-600 hover:text-gray-900">Özellikler</a>
              <a href="#pricing" className="text-gray-600 hover:text-gray-900">Fiyatlar</a>
              <a href="#demo" className="text-gray-600 hover:text-gray-900">Demo</a>
              <button 
                onClick={() => navigate('/login')}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                Giriş Yap
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-600 to-blue-800 text-white">
        <div className="absolute inset-0 bg-black opacity-10"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 md:py-32">
          <div className="text-center">
            <div className="inline-flex items-center space-x-2 bg-blue-500 bg-opacity-30 px-4 py-2 rounded-full mb-8">
              <Zap className="w-5 h-5" />
              <span className="text-sm font-medium">Türkiye'nin En Hızlı Büyüyen PMS'i</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Otel Yönetiminde
              <br />
              <span className="text-blue-200">Yeni Nesil Deneyim</span>
            </h1>
            <p className="text-xl md:text-2xl text-blue-100 mb-12 max-w-3xl mx-auto">
              AI destekli, ultra hızlı ve kapsamlı otel yönetim sistemi ile operasyonlarınızı optimize edin
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <button 
                onClick={() => document.getElementById('demo').scrollIntoView({ behavior: 'smooth' })}
                className="bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-50 transition flex items-center justify-center space-x-2"
              >
                <span>Ücretsiz Demo İsteyin</span>
                <ArrowRight className="w-5 h-5" />
              </button>
              <button 
                onClick={() => navigate('/login')}
                className="bg-blue-500 bg-opacity-30 border-2 border-white text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-opacity-40 transition"
              >
                Hemen Başlayın
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-4xl font-bold text-blue-600 mb-2">{stat.value}</div>
                <div className="text-gray-600">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              İhtiyacınız Olan Her Şey
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Rezervasyondan gelir yönetimine, kat hizmetlerinden raporlamaya kadar tüm otel operasyonlarınızı tek platformda yönetin
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition">
                <div className="text-blue-600 mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Key Benefits */}
      <section className="py-20 bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-6">
                <Zap className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Kolay Kullanım</h3>
              <p className="text-gray-600">
                Sezgisel arayüz ve 15 dakikalık eğitim ile personeliniz hemen kullanmaya başlayabilir
              </p>
            </div>
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-600 rounded-full mb-6">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Güvenli</h3>
              <p className="text-gray-600">
                GDPR uyumlu, şifrelenmiş veri saklama ve güvenli ödeme işlemleri
              </p>
            </div>
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-600 rounded-full mb-6">
                <Globe className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Global</h3>
              <p className="text-gray-600">
                8 dil desteği ve tüm OTA kanalları ile dünya çapında kullanım
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Basit ve Şeffaf Fiyatlandırma
            </h2>
            <p className="text-xl text-gray-600">
              Otel büyüklüğünüze uygun planı seçin, istediğiniz zaman değiştirin
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {pricingPlans.map((plan, index) => (
              <div 
                key={index} 
                className={`bg-white rounded-2xl shadow-lg p-8 ${
                  plan.popular ? 'ring-2 ring-blue-600 relative' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                    <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                      En Popüler
                    </span>
                  </div>
                )}
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                  <div className="flex items-baseline justify-center">
                    <span className="text-5xl font-bold text-blue-600">{plan.price}</span>
                    <span className="text-gray-600 ml-2">{plan.period}</span>
                  </div>
                </div>
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start">
                      <CheckCircle className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-600">{feature}</span>
                    </li>
                  ))}
                </ul>
                <button 
                  onClick={() => document.getElementById('demo').scrollIntoView({ behavior: 'smooth' })}
                  className={`w-full py-3 rounded-lg font-semibold transition ${
                    plan.popular
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  Başlayın
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Request Form */}
      <section id="demo" className="py-20 bg-gradient-to-br from-blue-600 to-blue-800 text-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ücretsiz Demo İsteyin
            </h2>
            <p className="text-xl text-blue-100">
              RoomOps PMS'i kendiniz deneyimleyin. Hemen iletişime geçin.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <form onSubmit={handleDemoRequest} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Adınız Soyadınız
                  </label>
                  <input
                    type="text"
                    required
                    value={demoForm.name}
                    onChange={(e) => setDemoForm({...demoForm, name: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    placeholder="Ahmet Yılmaz"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email Adresiniz
                  </label>
                  <input
                    type="email"
                    required
                    value={demoForm.email}
                    onChange={(e) => setDemoForm({...demoForm, email: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    placeholder="ahmet@otelim.com"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Telefon Numaranız
                  </label>
                  <input
                    type="tel"
                    required
                    value={demoForm.phone}
                    onChange={(e) => setDemoForm({...demoForm, phone: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    placeholder="+90 555 123 4567"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Oda Sayısı
                  </label>
                  <input
                    type="number"
                    required
                    value={demoForm.roomCount}
                    onChange={(e) => setDemoForm({...demoForm, roomCount: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    placeholder="50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Otel Adı
                </label>
                <input
                  type="text"
                  required
                  value={demoForm.hotelName}
                  onChange={(e) => setDemoForm({...demoForm, hotelName: e.target.value})}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                  placeholder="Grand Hotel Istanbul"
                />
              </div>

              <button
                type="submit"
                disabled={submitStatus === 'sending'}
                className="w-full bg-blue-600 text-white py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition disabled:bg-blue-400"
              >
                {submitStatus === 'sending' ? 'Gönderiliyor...' : 'Demo Talebini Gönder'}
              </button>

              {submitStatus === 'success' && (
                <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
                  ✓ Demo talebiniz alındı! En kısa sürede sizinle iletişime geçeceğiz.
                </div>
              )}

              {submitStatus === 'error' && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
                  Bir hata oluştu. Lütfen tekrar deneyin.
                </div>
              )}
            </form>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Hotel className="w-8 h-8 text-blue-400" />
                <span className="text-xl font-bold">RoomOps PMS</span>
              </div>
              <p className="text-gray-400">
                Otel yönetiminde yeni nesil deneyim
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Ürün</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#features" className="hover:text-white">Özellikler</a></li>
                <li><a href="#pricing" className="hover:text-white">Fiyatlandırma</a></li>
                <li><a href="#demo" className="hover:text-white">Demo</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Şirket</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#" className="hover:text-white">Hakkımızda</a></li>
                <li><a href="#" className="hover:text-white">İletişim</a></li>
                <li><a href="#" className="hover:text-white">Blog</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Destek</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#" className="hover:text-white">Dokümantasyon</a></li>
                <li><a href="#" className="hover:text-white">Yardım Merkezi</a></li>
                <li><a href="#" className="hover:text-white">KVKK</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-gray-400">
            <p>&copy; 2025 RoomOps PMS. Tüm hakları saklıdır.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
