import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { ArrowRight, CalendarDays, Ticket, Users, Layers, AlertCircle } from "lucide-react";

import { api, apiErrorMessage, getUser } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";

function StatCard({ title, value, icon: Icon, to, testId }) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex items-end justify-between">
        <div className="text-3xl font-semibold text-foreground" data-testid={testId}>
          {value}
        </div>
        {to ? (
          <Button asChild variant="outline" size="sm" className="gap-2">
            <Link to={to}>
              Aç <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const user = getUser();
  const isHotel = (user?.roles || []).includes("hotel_admin") || (user?.roles || []).includes("hotel_staff");
  const isAgency = (user?.roles || []).includes("agency_admin") || (user?.roles || []).includes("agency_agent");


  const [caseCounters, setCaseCounters] = useState({ open: 0, waiting: 0, in_progress: 0 });

  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      setError("");
      try {
        const [a, b, c] = await Promise.all([
          api.get("/reports/reservations-summary"),
          api.get("/reports/sales-summary"),
          api.get("/ops-cases/counters"),
        ]);
        setResSummary(a.data || []);
        setSales(b.data || []);
        setCaseCounters(c.data || { open: 0, waiting: 0, in_progress: 0 });
      } catch (e) {
        const msg = apiErrorMessage(e);
        // dashboard'da krmz hata gstermek yerine sessizce bofa dryoruz.
        const status = e?.response?.status;
        if (msg !== "Not Found" && status !== 403) {
          setError(msg);
        }
