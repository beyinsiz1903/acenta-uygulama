import React from "react";
import { useNavigate } from "react-router-dom";
import OnboardingWizard from "../components/OnboardingWizard";

export default function OnboardingWizardPage() {
  const navigate = useNavigate();
  return (
    <OnboardingWizard
      onComplete={() => {
        // Force reload to re-check onboarding state in AppShell
        window.location.href = "/app";
      }}
    />
  );
}
