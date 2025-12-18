import React from "react";
import { useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { Button } from "../components/ui/button";
import { clearToken } from "../lib/api";

export default function UnauthorizedPage() {
  const navigate = useNavigate();

  const user = React.useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("acenta_user"));
    } catch {
      return null;
    }
  }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="flex justify-center">
          <div className="h-20 w-20 rounded-full bg-destructive/10 flex items-center justify-center">
            <ShieldAlert className="h-10 w-10 text-destructive" />
          </div>
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">Yetkiniz Yok</h1>
          <p className="text-muted-foreground">
            Bu sayfaya erişim yetkiniz bulunmamaktadır.
          </p>
        </div>

        {user && (
          <div className="bg-muted/50 rounded-lg p-4 text-sm text-left space-y-1">
            <div>
              <span className="text-muted-foreground">Email:</span>{" "}
              <span className="font-mono text-foreground">{user.email}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Roller:</span>{" "}
              <span className="font-mono text-foreground">
                {user.roles?.join(", ") || "Yok"}
              </span>
            </div>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button
            variant="outline"
            onClick={() => navigate(-1)}
          >
            Geri Dön
          </Button>
          <Button
            onClick={() => {
              clearToken();
              window.location.href = "/login";
            }}
          >
            Çıkış Yap
          </Button>
        </div>
      </div>
    </div>
  );
}
