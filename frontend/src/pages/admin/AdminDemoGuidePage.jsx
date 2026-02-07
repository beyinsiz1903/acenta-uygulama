import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import {
  Presentation, RefreshCw, ChevronLeft, ChevronRight,
  ExternalLink, Clock, MessageCircle, Monitor
} from "lucide-react";

export default function AdminDemoGuidePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/system/demo-guide");
      setData(res.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const steps = data?.steps || [];
  const step = steps[currentStep];
  const progress = steps.length > 0 ? ((currentStep + 1) / steps.length) * 100 : 0;

  const goToScreen = (path) => {
    window.open(path, "_blank");
  };

  return (
    <div className="space-y-6" data-testid="demo-guide-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Presentation className="h-6 w-6 text-violet-600" />
          <h1 className="text-2xl font-bold text-gray-900">Demo Rehberi</h1>
          {data && <Badge variant="outline">{data.total_time}</Badge>}
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : !step ? (
        <div className="text-center py-12 text-gray-500">Yüklenemedi</div>
      ) : (
        <div className="space-y-4" data-testid="demo-guide-content">
          {/* Progress Bar */}
          <div className="bg-gray-200 rounded-full h-2">
            <div
              className="bg-violet-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Step Navigator */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline" size="sm"
              disabled={currentStep === 0}
              onClick={() => setCurrentStep(s => s - 1)}
            >
              <ChevronLeft className="h-4 w-4 mr-1" /> \u00d6nceki
            </Button>
            <span className="text-sm text-gray-500">
              {currentStep + 1} / {steps.length}
            </span>
            <Button
              variant="outline" size="sm"
              disabled={currentStep >= steps.length - 1}
              onClick={() => setCurrentStep(s => s + 1)}
            >
              Sonraki <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>

          {/* Current Step Card */}
          <div className="bg-white border-2 border-violet-200 rounded-xl shadow-lg overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-4 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Clock className="h-4 w-4 opacity-75" />
                    <span className="text-sm opacity-75">{step.time}</span>
                  </div>
                  <h2 className="text-xl font-bold">{step.title}</h2>
                </div>
                <Button
                  size="sm"
                  className="bg-white/20 hover:bg-white/30 text-white border-white/30"
                  onClick={() => goToScreen(step.screen)}
                >
                  <Monitor className="h-4 w-4 mr-1" />
                  {step.screen_label}
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              </div>
            </div>

            {/* Body */}
            <div className="px-6 py-4 space-y-4">
              {/* Message */}
              <div className="flex items-start gap-3 bg-violet-50 rounded-lg p-4">
                <MessageCircle className="h-5 w-5 text-violet-500 flex-shrink-0 mt-0.5" />
                <p className="text-gray-800 italic">"{step.message}"</p>
              </div>

              {/* Talking Points */}
              <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Konu\u015fma Noktalar\u0131</h3>
                <ul className="space-y-2">
                  {step.talking_points?.map((tp, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-violet-100 text-violet-700 text-xs flex items-center justify-center font-bold mt-0.5">
                        {i + 1}
                      </span>
                      <span className="text-sm text-gray-700">{tp}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Sub-screens */}
              {step.sub_screens && step.sub_screens.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Ek Ekranlar</h3>
                  <div className="flex flex-wrap gap-2">
                    {step.sub_screens.map((ss, i) => (
                      <button
                        key={i}
                        onClick={() => goToScreen(ss.path)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg text-sm hover:bg-indigo-100 transition-colors"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {ss.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Step Thumbnails */}
          <div className="flex gap-1 overflow-x-auto pb-2">
            {steps.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setCurrentStep(i)}
                className={`flex-shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  i === currentStep
                    ? "bg-violet-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {s.time.split("-")[0]}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
