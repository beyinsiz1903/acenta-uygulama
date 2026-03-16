import React from "react";
import { Button } from "../../../components/ui/button";

export function FilterPresetsBar({
  presets,
  selectedPresetId,
  onSelectPreset,
  onSavePreset,
  onDeletePreset,
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap" data-testid="filter-presets-bar">
      <select
        data-testid="preset-select"
        className="h-8 rounded-md border bg-background px-2 text-xs"
        value={selectedPresetId}
        onChange={(e) => {
          const id = e.target.value;
          onSelectPreset(id);
        }}
      >
        <option value="">Preset sec...</option>
        {presets.map((p) => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => {
          const name = window.prompt("Preset adi");
          if (!name || !name.trim()) return;
          onSavePreset(name.trim());
        }}
        data-testid="save-preset-btn"
      >
        Preset Kaydet
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={!selectedPresetId}
        onClick={() => {
          if (!selectedPresetId) return;
          const ok = window.confirm("Bu preset silinsin mi?");
          if (!ok) return;
          onDeletePreset(selectedPresetId);
        }}
        data-testid="delete-preset-btn"
      >
        Preset Sil
      </Button>
      {presets.length === 0 && (
        <span className="text-xs text-muted-foreground">
          Filtreleri ayarlayip Preset Kaydet ile tekrar kullanabilirsiniz.
        </span>
      )}
    </div>
  );
}
