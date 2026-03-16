import React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  Shield, Activity, Server, Zap, Lock, Scale, Database,
  CheckCircle2, Play, Target, Gauge, Radio, FlaskConical,
  Users, FileCheck, Truck, Plug,
} from "lucide-react";

/* ─── Already-external tab files ─── */
import SupplierActivationTab from "./SupplierActivationTab";
import StressTestTab from "./StressTestTab";
import PilotLaunchTab from "./PilotLaunchTab";
import SupplierSettingsTab from "./SupplierSettingsTab";

/* ─── Extracted feature tabs ─── */
import { OverviewTab, ExecutionTab, CertificationTab } from "../../features/platform-hardening/components/OverviewExecutionTabs";
import { TrafficTestingTab, WorkerStrategyTab } from "../../features/platform-hardening/components/InfrastructureTabs";
import { ObservabilityTab, PerformanceTab, TenantSafetyTab, SecretsTab } from "../../features/platform-hardening/components/MonitoringTabs";
import { PlaybooksTab, ScalingTab, DRTab, ChecklistTab } from "../../features/platform-hardening/components/OperationsTabs";
import {
  LiveInfrastructureTab, PerformanceBaselineTab, IncidentSimulationTab,
  TenantIsolationRealTab, DryRunTab, OnboardingTab,
  GoLiveCertificationTab, SecurityDashboardTab,
} from "../../features/platform-hardening/components/ActivationTabs";

export default function PlatformHardeningPage() {
  return (
    <div data-testid="platform-hardening-page" className="p-4 md:p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-7 h-7 text-emerald-400" />
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Platform Hardening Dashboard</h1>
          <p className="text-xs text-zinc-500">Enterprise production readiness — Execution Phase</p>
        </div>
      </div>

      <Tabs defaultValue="golive" className="space-y-4">
        <TabsList data-testid="hardening-tabs" className="bg-zinc-900 border border-zinc-800 flex-wrap h-auto gap-1 p-1">
          {/* Production Activation Tabs */}
          <TabsTrigger value="golive" className="text-xs gap-1 data-[state=active]:bg-emerald-700 data-[state=active]:text-white"><FileCheck className="w-3.5 h-3.5" />Go-Live</TabsTrigger>
          <TabsTrigger value="suppliers" className="text-xs gap-1 data-[state=active]:bg-purple-700 data-[state=active]:text-white"><Truck className="w-3.5 h-3.5" />Suppliers</TabsTrigger>
          <TabsTrigger value="security" className="text-xs gap-1 data-[state=active]:bg-red-700 data-[state=active]:text-white"><Shield className="w-3.5 h-3.5" />Security</TabsTrigger>
          <TabsTrigger value="infra" className="text-xs gap-1"><Radio className="w-3.5 h-3.5" />Infrastructure</TabsTrigger>
          <TabsTrigger value="perfbaseline" className="text-xs gap-1"><Gauge className="w-3.5 h-3.5" />Performance</TabsTrigger>
          <TabsTrigger value="incidents" className="text-xs gap-1"><FlaskConical className="w-3.5 h-3.5" />Incidents</TabsTrigger>
          <TabsTrigger value="isolation" className="text-xs gap-1"><Lock className="w-3.5 h-3.5" />Isolation</TabsTrigger>
          <TabsTrigger value="dryrun" className="text-xs gap-1"><Play className="w-3.5 h-3.5" />Dry Run</TabsTrigger>
          <TabsTrigger value="onboarding" className="text-xs gap-1"><Users className="w-3.5 h-3.5" />Onboarding</TabsTrigger>
          <TabsTrigger value="stresstest" className="text-xs gap-1 data-[state=active]:bg-orange-700 data-[state=active]:text-white"><Zap className="w-3.5 h-3.5" />Stress Test</TabsTrigger>
          <TabsTrigger value="pilot" className="text-xs gap-1 data-[state=active]:bg-sky-700 data-[state=active]:text-white"><Play className="w-3.5 h-3.5" />Pilot Launch</TabsTrigger>
          <TabsTrigger value="supplier-settings" className="text-xs gap-1 data-[state=active]:bg-emerald-700 data-[state=active]:text-white"><Plug className="w-3.5 h-3.5" />Supplier Settings</TabsTrigger>
          {/* Design & Execution Tabs */}
          <TabsTrigger value="overview" className="text-xs gap-1"><Shield className="w-3.5 h-3.5" />Overview</TabsTrigger>
          <TabsTrigger value="execution" className="text-xs gap-1"><Target className="w-3.5 h-3.5" />Execution</TabsTrigger>
          <TabsTrigger value="traffic" className="text-xs gap-1"><Zap className="w-3.5 h-3.5" />Traffic</TabsTrigger>
          <TabsTrigger value="workers" className="text-xs gap-1"><Server className="w-3.5 h-3.5" />Workers</TabsTrigger>
          <TabsTrigger value="observability" className="text-xs gap-1"><Activity className="w-3.5 h-3.5" />Observability</TabsTrigger>
          <TabsTrigger value="secrets" className="text-xs gap-1"><Lock className="w-3.5 h-3.5" />Secrets</TabsTrigger>
          <TabsTrigger value="scaling" className="text-xs gap-1"><Scale className="w-3.5 h-3.5" />Scaling</TabsTrigger>
          <TabsTrigger value="dr" className="text-xs gap-1"><Database className="w-3.5 h-3.5" />DR</TabsTrigger>
          <TabsTrigger value="checklist" className="text-xs gap-1"><CheckCircle2 className="w-3.5 h-3.5" />Checklist</TabsTrigger>
        </TabsList>

        {/* Production Activation */}
        <TabsContent value="golive"><GoLiveCertificationTab /></TabsContent>
        <TabsContent value="suppliers"><SupplierActivationTab /></TabsContent>
        <TabsContent value="security"><SecurityDashboardTab /></TabsContent>
        <TabsContent value="infra"><LiveInfrastructureTab /></TabsContent>
        <TabsContent value="perfbaseline"><PerformanceBaselineTab /></TabsContent>
        <TabsContent value="incidents"><IncidentSimulationTab /></TabsContent>
        <TabsContent value="isolation"><TenantIsolationRealTab /></TabsContent>
        <TabsContent value="dryrun"><DryRunTab /></TabsContent>
        <TabsContent value="onboarding"><OnboardingTab /></TabsContent>
        <TabsContent value="stresstest"><StressTestTab /></TabsContent>
        <TabsContent value="pilot"><PilotLaunchTab /></TabsContent>
        <TabsContent value="supplier-settings"><SupplierSettingsTab /></TabsContent>
        {/* Design & Execution */}
        <TabsContent value="overview"><OverviewTab /></TabsContent>
        <TabsContent value="execution"><ExecutionTab /></TabsContent>
        <TabsContent value="traffic"><TrafficTestingTab /></TabsContent>
        <TabsContent value="workers"><WorkerStrategyTab /></TabsContent>
        <TabsContent value="observability"><ObservabilityTab /></TabsContent>
        <TabsContent value="secrets"><SecretsTab /></TabsContent>
        <TabsContent value="scaling"><ScalingTab /></TabsContent>
        <TabsContent value="dr"><DRTab /></TabsContent>
        <TabsContent value="checklist"><ChecklistTab /></TabsContent>
      </Tabs>
    </div>
  );
}
