(() => {
  const start = document.getElementById("iniciar-leitura");
  if (!start) return;
  const stop = document.getElementById("parar-leitura");
  const video = document.getElementById("camera-frequencia");
  const status = document.getElementById("camera-status");
  let stream, timer;
  function cleanup() {
    clearTimeout(timer);
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
    video.hidden = stop.hidden = true;
    start.disabled = false;
  }
  stop.addEventListener("click", cleanup);
  window.addEventListener("pagehide", cleanup);
  start.addEventListener("click", async () => {
    if (!window.BarcodeDetector || !navigator.mediaDevices?.getUserMedia) {
      status.textContent = "Este navegador não oferece leitura direta. Use a câmera do celular para abrir o QR Code ou confirme na lista de participantes.";
      return;
    }
    start.disabled = true;
    try {
      const detector = new BarcodeDetector({ formats: ["qr_code"] });
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.srcObject = stream;
      video.hidden = stop.hidden = false;
      await video.play();
      status.textContent = "Aponte a câmera para o QR Code do comprovante.";
      async function scan() {
        if (!stream) return;
        try {
          for (const result of await detector.detect(video)) {
            const url = new URL(result.rawValue);
            if (url.origin === location.origin && /\/frequencia\/validar\/[^/]+\/$/.test(url.pathname)) {
              cleanup();
              location.assign(url.href);
              return;
            }
          }
          timer = setTimeout(scan, 250);
        } catch {
          cleanup();
          status.textContent = "Não foi possível ler. Use a câmera do celular ou a chamada manual.";
        }
      }
      scan();
    } catch {
      cleanup();
      status.textContent = "Câmera indisponível. Use a câmera do celular ou a chamada manual.";
    }
  });
})();
