import React, { useState, useEffect } from "react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../../components/ui/dialog";
import { toast } from "../../../components/ui/sonner";
import { Loader2 } from "lucide-react";
import { refundsApi } from "../api";
import { apiErrorMessage } from "../../../lib/api";

export function RefundApproveDialog({ open, onOpenChange, caseData, onApproved }) {
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const refundable = caseData?.computed?.refundable ?? 0;

  useEffect(() => {
    if (open && refundable) setAmount(String(refundable));
  }, [open, refundable]);

  const onSubmit = async () => {
    const parsed = parseFloat(amount);
    if (!parsed || parsed <= 0 || parsed > refundable + 1e-6) {
      toast({ title: "Onaylanan tutar gecersiz", description: `Tutar 0'dan buyuk ve iade edilebilir tutardan ( ${refundable.toFixed(2)} ) kucuk veya esit olmalidir.`, variant: "destructive" });
      return;
    }
    try {
      setSubmitting(true);
      await refundsApi.approveStep1(caseData.case_id, parsed);
      toast({ title: "1. onay verildi" });
      onApproved();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Onaylama basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>1. Onay</DialogTitle></DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">
            Refundable (computed): <strong>{refundable.toFixed(2)}</strong>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Onaylanan tutar</div>
            <Input data-testid="approve-amount-input" type="number" min={0} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Iptal</Button>
          <Button data-testid="approve-step1-submit" onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            1. Onayi Ver
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RefundApproveStep2Dialog({ open, onOpenChange, caseData, onApproved }) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (open) setNote(""); }, [open]);

  const onSubmit = async () => {
    try {
      setSubmitting(true);
      await refundsApi.approveStep2(caseData.case_id, note);
      toast({ title: "2. onay verildi" });
      onApproved();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Onaylama basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>2. Onay</DialogTitle></DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">
            Bu adimda ledger kayitlari olusturulur ve refund case &quot;approved&quot; durumuna alinir.
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Not (opsiyonel)</div>
            <Input data-testid="approve-step2-note" type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ops notu (opsiyonel)" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Iptal</Button>
          <Button data-testid="approve-step2-submit" onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            2. Onayi Ver
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RefundRejectDialog({ open, onOpenChange, caseData, onRejected }) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (open) setReason(""); }, [open]);

  const onSubmit = async () => {
    try {
      setSubmitting(true);
      await refundsApi.reject(caseData.case_id, reason);
      toast({ title: "Refund reddedildi" });
      onRejected();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Red basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Refund Reddet</DialogTitle></DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Red sebebi</div>
            <Input data-testid="reject-reason-input" type="text" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Ops notu (opsiyonel)" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Iptal</Button>
          <Button data-testid="reject-submit" onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Reddet
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RefundMarkPaidDialog({ open, onOpenChange, caseData, onMarked }) {
  const [paymentRef, setPaymentRef] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (open) setPaymentRef(""); }, [open]);

  const onSubmit = async () => {
    if (!paymentRef.trim()) {
      toast({ title: "Odeme referansi gerekli", description: "Lutfen bir odeme referansi girin.", variant: "destructive" });
      return;
    }
    try {
      setSubmitting(true);
      await refundsApi.markPaid(caseData.case_id, paymentRef.trim());
      toast({ title: "Refund odendi olarak isaretlendi" });
      onMarked();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Islem basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Odendi olarak isaretle</DialogTitle></DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Odeme referansi</div>
            <Input data-testid="mark-paid-ref-input" type="text" value={paymentRef} onChange={(e) => setPaymentRef(e.target.value)} placeholder="Odeme dekont/ref no" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Iptal</Button>
          <Button data-testid="mark-paid-submit" onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Odendi
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
