import React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "../components/ui/button";
import { clearToken } from "../lib/api";

export default function ErrorContextPage() {
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
          <div className="h-20 w-20 rounded-full bg-yellow-500/10 flex items-center justify-center">
            <AlertTriangle className="h-10 w-10 text-yellow-500" />
          </div>
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">Eksik Context</h1>
          <p className="text-muted-foreground">
            Kullanıcı hesabınızda gerekli context bilgisi eksik.
            <br />
            Lütfen sistem yöneticinizle iletişime geçin.
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
            <div>
              <span className="text-muted-foreground">Agency ID:</span>{" "}
              <span className="font-mono text-foreground">
                {user.agency_id || "❌ Eksik"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Hotel ID:</span>{" "}
              <span className="font-mono text-foreground">
                {user.hotel_id || "❌ Eksik"}
              </span>
            </div>
          </div>
        )}

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
  );
}
