import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./ui/button";

export class PageErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[PageErrorBoundary]", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 text-center p-8" data-testid="page-error-boundary">
          <AlertTriangle className="h-12 w-12 text-amber-500" />
          <h2 className="text-lg font-semibold text-foreground">Bu sayfa yüklenirken bir hata oluştu</h2>
          <p className="text-sm text-muted-foreground max-w-md">
            Sayfa beklenmedik bir hatayla karşılaştı. Sayfayı yenileyerek tekrar deneyebilirsiniz.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            data-testid="error-boundary-reload-btn"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Sayfayı Yenile
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
