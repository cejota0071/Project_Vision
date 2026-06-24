// Auxilia o painel a emitir e baixar PDF do laudo.
// Espera que o backend exponha:
// - POST /laudos/{exame_id}
// - GET  /laudos/{laudo_id}/download

(function () {
  window.gregPDF = {
    _lastLaudoId: localStorage.getItem('greg_last_laudo_id') || null,

    async emitirPDF(exameId, token, body = {}) {
      const base = window.gregConfig?.apiUrl || '';
      const url = `${base}/laudos/${exameId}`;

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Erro ao gerar PDF (HTTP ${res.status})`);
      }

      return res.json(); // LaudoOut
    },

    async baixarPDF(laudoId, token) {
      const base = window.gregConfig?.apiUrl || '';
      const url = `${base}/laudos/${laudoId}/download`;

      // Como é FileResponse, melhor usar window.location com token (ou chamar fetch e blob).
      // Implementação simples/compatível: fetch->blob.
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        throw new Error(`Erro ao baixar PDF (HTTP ${res.status})`);
      }
      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `laudo_${laudoId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(downloadUrl);
    },
  };
})();

