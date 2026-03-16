import React, { useState, useEffect } from "react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Badge } from "../../../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../../components/ui/dialog";
import { toast } from "../../../components/ui/sonner";
import { Loader2, Trash2 } from "lucide-react";
import { refundsApi } from "../api";
import { apiErrorMessage } from "../../../lib/api";
import { isPdfDoc, TAG_OPTIONS, TAG_LABELS } from "../utils";

function PDFPreviewDialog({ previewOpen, setPreviewOpen, previewUrl, setPreviewUrl, previewTitle, previewLoading, previewError }) {
  return (
    <Dialog
      open={previewOpen}
      onOpenChange={(v) => {
        if (!v && previewUrl) window.URL.revokeObjectURL(previewUrl);
        if (!v) setPreviewUrl("");
        setPreviewOpen(v);
      }}
    >
      <DialogContent className="max-w-4xl">
        <DialogHeader><DialogTitle className="text-sm">{previewTitle || "PDF Onizleme"}</DialogTitle></DialogHeader>
        {previewLoading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /><span>Yukleniyor...</span></div>
        ) : previewError ? (
          <div className="text-xs text-destructive">{previewError}</div>
        ) : previewUrl ? (
          <iframe src={previewUrl} title="PDF Preview" className="w-full h-[70vh] rounded border" />
        ) : (
          <div className="text-xs text-muted-foreground">Onizleme icin bir PDF secin.</div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function RefundDocumentsSection({ caseData }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [tag, setTag] = useState("dekont");
  const [note, setNote] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  const hasCase = !!caseData?.case_id;

  const load = async () => {
    if (!hasCase) return;
    try {
      setLoading(true); setError("");
      const resp = await refundsApi.listDocuments(caseData.case_id);
      setItems(resp?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hasCase) load(); else setItems([]);
  }, [caseData?.case_id]);

  const onUpload = async () => {
    if (!file) { toast({ title: "Dosya secilmedi", variant: "destructive" }); return; }
    try {
      setUploading(true);
      await refundsApi.uploadDocument(caseData.case_id, { file, tag, note });
      toast({ title: "Dokuman yuklendi" });
      setFile(null); setNote("");
      await load();
    } catch (e) {
      toast({ title: "Dokuman yuklenemedi", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (doc) => {
    try {
      await refundsApi.deleteDocument(doc.document_id);
      toast({ title: "Dokuman silindi" });
      await load();
    } catch (e) {
      toast({ title: "Dokuman silinemedi", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  const onDownload = async (doc) => {
    try {
      const blobData = await refundsApi.downloadDocument(doc.document_id);
      const blob = new Blob([blobData], { type: doc.content_type || "application/octet-stream" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = doc.filename || "document";
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: "Indirme basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  if (!hasCase) return null;

  return (
    <div className="rounded-lg border bg-muted/20 p-3 space-y-3" data-testid="refund-documents-section">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-muted-foreground">Dokumanlar</div>
      </div>

      <div className="flex flex-wrap items-end gap-2 text-xs">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Etiket</span>
          <select className="border rounded px-2 py-1 text-xs bg-background" value={tag} onChange={(e) => setTag(e.target.value)}>
            {TAG_OPTIONS.map((t) => <option key={t} value={t}>{TAG_LABELS[t]}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1 min-w-[160px] flex-1">
          <span className="text-xs text-muted-foreground">Not (opsiyonel)</span>
          <Input type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Kisa aciklama" />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Dosya</span>
          <Input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <Button size="sm" onClick={onUpload} disabled={uploading || !file} className="mt-4" data-testid="upload-document-btn">
          {uploading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}Yukle
        </Button>
      </div>

      {loading ? (
        <div className="text-xs text-muted-foreground">Dokumanlar yukleniyor...</div>
      ) : error ? (
        <div className="text-xs text-destructive">{error}</div>
      ) : !items.length ? (
        <div className="text-xs text-muted-foreground">Bu refund icin dokuman yok.</div>
      ) : (
        <div className="mt-2 space-y-1 text-xs">
          {items.map((doc) => {
            const tagValue = doc.tag || "diger";
            const isKnownTag = TAG_OPTIONS.includes(tagValue);
            const badgeText = isKnownTag ? TAG_LABELS[tagValue] : `Diger (${tagValue})`;
            return (
              <div key={doc.document_id} className="flex items-center justify-between gap-2 rounded border bg-background px-2 py-1">
                <div className="flex items-center gap-2 min-w-0">
                  <Badge variant="outline" className="text-2xs uppercase">{badgeText}</Badge>
                  <button type="button" className="text-xs text-blue-600 hover:underline truncate max-w-[220px] text-left" onClick={() => onDownload(doc)} title={doc.filename}>
                    {doc.filename}
                  </button>
                  <span className="text-xs text-muted-foreground">{doc.size_bytes != null ? `${Math.round(doc.size_bytes / 1024)} KB` : ""}</span>
                  {isPdfDoc(doc) && (
                    <Button size="xs" variant="outline" disabled={previewLoading}
                      onClick={async () => {
                        try {
                          setPreviewError(""); setPreviewTitle(doc.filename || "PDF Onizleme");
                          setPreviewOpen(true);
                          if (previewUrl) window.URL.revokeObjectURL(previewUrl);
                          setPreviewUrl(""); setPreviewLoading(true);
                          const blobData = await refundsApi.downloadDocument(doc.document_id);
                          const blob = new Blob([blobData], { type: "application/pdf" });
                          setPreviewUrl(window.URL.createObjectURL(blob));
                        } catch (e) {
                          setPreviewError(apiErrorMessage(e));
                        } finally {
                          setPreviewLoading(false);
                        }
                      }}>
                      Onizle
                    </Button>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{doc.created_by_email}</span>
                  <span>{doc.created_at ? new Date(doc.created_at).toLocaleString() : ""}</span>
                  <Button size="icon" variant="ghost" className="h-6 w-6 text-destructive" onClick={() => onDelete(doc)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <PDFPreviewDialog previewOpen={previewOpen} setPreviewOpen={setPreviewOpen} previewUrl={previewUrl} setPreviewUrl={setPreviewUrl} previewTitle={previewTitle} previewLoading={previewLoading} previewError={previewError} />
    </div>
  );
}
